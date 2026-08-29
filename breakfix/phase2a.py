from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_contract import validate_phase2a_baseline_response, validate_phase2a_breakfix_response
from .benchmark import after_dir
from .diffing import make_diff
from .evidence import write_json, write_text
from .executor import run_experiment, run_visible_tests
from .experiments import EXPERIMENTS, experiment_by_id, payload_for


PHASE2A_CASE_IDS = tuple(f"h{index:02d}" for index in range(1, 15))


def holdout_case_dir(root: Path, case_id: str) -> Path:
    return root / "benchmark" / "phase2a_holdout" / case_id


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_truth(root: Path) -> dict[str, Any]:
    return json.loads((root / "benchmark" / "phase2a_ground_truth.json").read_text(encoding="utf-8"))


def _load_replay(root: Path, lane: str, case_id: str) -> tuple[dict[str, Any] | None, str | None]:
    path = root / "trajectories" / "phase2a" / lane / case_id / "replay.json"
    if not path.exists():
        return None, f"missing replay artifact: {_relative(root, path)}"
    try:
        replay = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid replay JSON: {exc.msg} at character {exc.pos}"
    if not isinstance(replay, dict) or not isinstance(replay.get("response_text"), str):
        return None, "replay must be an object with a response_text string"
    replay["replay_path"] = _relative(root, path)
    return replay, None


def _metadata(replays: list[dict[str, Any]]) -> dict[str, Any]:
    providers = sorted({replay.get("provider", "unknown") for replay in replays})
    models = sorted({replay.get("model", "unknown") for replay in replays})
    reasoning = sorted({replay.get("reasoning_effort", "unknown") for replay in replays})

    def total_if_complete(field: str) -> int | float | None:
        values = [replay.get(field) for replay in replays]
        return sum(values) if values and all(isinstance(value, (int, float)) for value in values) else None

    return {
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "reasoning_effort": reasoning[0] if len(reasoning) == 1 else reasoning,
        "temperature": replays[0].get("temperature") if replays else None,
        "max_output_tokens": replays[0].get("max_output_tokens") if replays else None,
        "model_calls": sum(int(replay.get("model_calls", 1)) for replay in replays),
        "runtime_ms": total_if_complete("runtime_ms"),
        "latency_ms": total_if_complete("latency_ms"),
        "input_tokens": total_if_complete("input_tokens"),
        "output_tokens": total_if_complete("output_tokens"),
        "total_tokens": total_if_complete("total_tokens"),
        "monetary_cost_usd": total_if_complete("monetary_cost_usd"),
        "retries": sum(int(replay.get("retries", 0)) for replay in replays),
    }


def _evaluate_execution(truth: dict[str, Any], experiment_id: str, execution: dict[str, Any]) -> dict[str, Any]:
    expected_outputs = truth.get("expected_outputs", {})
    has_oracle = experiment_id in expected_outputs
    expected = expected_outputs.get(experiment_id)
    matches_expected = bool(has_oracle and not execution.get("process_failed") and execution.get("output") == expected)
    execution_proved_failure = bool(has_oracle and (execution.get("process_failed") or not matches_expected))
    evidence_complete = bool(
        execution.get("command")
        and isinstance(execution.get("stdout"), str)
        and isinstance(execution.get("stderr"), str)
        and (execution.get("exit_code") is not None or execution.get("timed_out"))
    )
    if not has_oracle:
        evidence_state = "UNSUPPORTED"
    elif execution_proved_failure and evidence_complete:
        evidence_state = "CONFIRMED_BREAK"
    elif matches_expected and evidence_complete:
        evidence_state = "CLEARED"
    else:
        evidence_state = "INCONCLUSIVE"
    return {
        "fault_experiment": experiment_id in truth.get("fault_experiments", []),
        "expected_output": expected,
        "actual_output": execution.get("output"),
        "matches_expected": matches_expected,
        "execution_proved_failure": execution_proved_failure,
        "evidence_complete": evidence_complete,
        "evidence_state": evidence_state,
    }


def _record_execution(root: Path, lane_dir: Path, case_id: str, experiment_id: str, execution: Any, evaluation: dict[str, Any], payload: dict[str, Any]) -> None:
    target = lane_dir / case_id / "execution" / experiment_id
    write_json(target / "result.json", {**execution.as_dict(), "payload": payload, "evaluation": evaluation})
    write_text(target / "stdout.log", execution.stdout)
    write_text(target / "stderr.log", execution.stderr)


def _breakfix_verdict(validation: dict[str, Any], records: list[dict[str, Any]]) -> str:
    if not validation.get("valid"):
        return "INCONCLUSIVE"
    if any(record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK" for record in records):
        return "DEFECT"
    if validation.get("unsupported_assumptions"):
        return "INCONCLUSIVE"
    if records and all(record["evaluation"]["evidence_state"] == "CLEARED" for record in records):
        return "SAFE"
    return "INCONCLUSIVE"


def _matrix_verdict(records: list[dict[str, Any]]) -> str:
    oracle_records = [record for record in records if record["evaluation"]["evidence_state"] != "UNSUPPORTED"]
    if any(record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK" for record in oracle_records):
        return "DEFECT"
    if oracle_records and all(record["evaluation"]["evidence_state"] == "CLEARED" for record in oracle_records):
        return "SAFE"
    return "INCONCLUSIVE"


def _lane_metrics(cases: list[dict[str, Any]], lane: str) -> dict[str, Any]:
    faults = [case for case in cases if case["fault"]]
    safe = [case for case in cases if not case["fault"]]
    correct = [case for case in cases if case[lane]["verdict"] == ("DEFECT" if case["fault"] else "SAFE")]
    fault_defects = [case for case in faults if case[lane]["verdict"] == "DEFECT"]
    safe_safe = [case for case in safe if case[lane]["verdict"] == "SAFE"]
    false_positives = [case for case in safe if case[lane]["verdict"] == "DEFECT"]
    false_approvals = [case for case in faults if case[lane]["verdict"] == "SAFE"]
    inconclusive = [case for case in cases if case[lane]["verdict"] == "INCONCLUSIVE"]
    executed = sum(case[lane].get("experiments_run", 0) for case in cases)
    confirmed = sum(len(case[lane].get("confirmed_experiments", [])) for case in cases)
    complete_confirmed = sum(case[lane].get("complete_confirmed_experiments", 0) for case in cases)
    return {
        "cases_total": len(cases),
        "fault_cases": len(faults),
        "safe_cases": len(safe),
        "correct_verdicts": len(correct),
        "correct_verdict_rate": len(correct) / len(cases) if cases else None,
        "fault_recall": len(fault_defects) / len(faults) if faults else None,
        "safe_case_specificity": len(safe_safe) / len(safe) if safe else None,
        "false_positives": len(false_positives),
        "false_positive_rate": len(false_positives) / len(safe) if safe else None,
        "false_approvals": len(false_approvals),
        "false_approval_rate": len(false_approvals) / len(faults) if faults else None,
        "inconclusive_cases": len(inconclusive),
        "experiments_executed": executed,
        "confirmed_breaks": confirmed,
        "confirmed_failure_rate": confirmed / len(faults) if faults else None,
        "executable_reproduction_rate": complete_confirmed / confirmed if confirmed else None,
        "experiments_per_confirmed_defect": executed / confirmed if confirmed else None,
        "execution_runtime_ms": sum(case[lane].get("execution_runtime_ms", 0) for case in cases),
    }


def _confusion_matrix(cases: list[dict[str, Any]], lane: str) -> dict[str, int]:
    return {
        "fault_as_defect": sum(case["fault"] and case[lane]["verdict"] == "DEFECT" for case in cases),
        "fault_as_safe": sum(case["fault"] and case[lane]["verdict"] == "SAFE" for case in cases),
        "fault_as_inconclusive": sum(case["fault"] and case[lane]["verdict"] == "INCONCLUSIVE" for case in cases),
        "safe_as_defect": sum((not case["fault"]) and case[lane]["verdict"] == "DEFECT" for case in cases),
        "safe_as_safe": sum((not case["fault"]) and case[lane]["verdict"] == "SAFE" for case in cases),
        "safe_as_inconclusive": sum((not case["fault"]) and case[lane]["verdict"] == "INCONCLUSIVE" for case in cases),
    }


def run_phase2a(root: Path) -> dict[str, Any]:
    root = root.resolve()
    truth_by_case = _load_truth(root)
    run_id = "phase2a-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root = root / "evidence" / run_id
    baseline_root = evidence_root / "baseline"
    fixed_root = evidence_root / "fixed-matrix"
    breakfix_root = evidence_root / "breakfix"
    comparison: dict[str, Any] = {
        "run_id": run_id,
        "phase": "2A-evidence-quality-lock",
        "holdout": "benchmark/phase2a_holdout",
        "cases": [],
        "integrity": {
            "ground_truth_used_by_evaluator_only": True,
            "real_subprocess_executions": True,
            "same_model_metadata_for_agent_lanes": True,
            "fixture_to_experiment_mapping_used_by_agent": False,
            "previous_phase1_5_cases_used_as_primary_evidence": False,
        },
    }
    baseline_replays: list[dict[str, Any]] = []
    breakfix_replays: list[dict[str, Any]] = []

    for case_id in PHASE2A_CASE_IDS:
        case_root = holdout_case_dir(root, case_id)
        public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
        truth = truth_by_case[case_id]
        diff = make_diff(case_root / "before" / "app.py", case_root / "after" / "app.py")
        visible = run_visible_tests(case_root / "after")
        baseline_replay, baseline_error = _load_replay(root, "baseline", case_id)
        breakfix_replay, breakfix_error = _load_replay(root, "breakfix", case_id)
        if baseline_replay:
            baseline_replays.append(baseline_replay)
        if breakfix_replay:
            breakfix_replays.append(breakfix_replay)
        baseline_validation = validate_phase2a_baseline_response(baseline_replay["response_text"]) if baseline_replay else {
            "valid": False,
            "validation_failures": [baseline_error],
            "findings": [],
            "verdict": None,
        }
        breakfix_validation = validate_phase2a_breakfix_response(breakfix_replay["response_text"]) if breakfix_replay else {
            "valid": False,
            "validation_failures": [breakfix_error],
            "assumptions": [],
            "selected_experiment_ids": [],
            "unsupported_assumptions": [],
        }

        fixed_records: list[dict[str, Any]] = []
        for experiment in EXPERIMENTS:
            payload = payload_for(experiment)
            execution = run_experiment(case_root / "after", experiment.id, payload)
            evaluation = _evaluate_execution(truth, experiment.id, execution.as_dict())
            _record_execution(root, fixed_root, case_id, experiment.id, execution, evaluation, payload)
            fixed_records.append({**execution.as_dict(), "evaluation": evaluation})

        selected = breakfix_validation.get("selected_experiment_ids", []) if breakfix_validation.get("valid") else []
        breakfix_records: list[dict[str, Any]] = []
        for experiment_id in selected:
            experiment = experiment_by_id(experiment_id)
            payload = payload_for(experiment)
            execution = run_experiment(case_root / "after", experiment.id, payload)
            evaluation = _evaluate_execution(truth, experiment.id, execution.as_dict())
            _record_execution(root, breakfix_root, case_id, experiment.id, execution, evaluation, payload)
            breakfix_records.append({**execution.as_dict(), "evaluation": evaluation})

        baseline_verdict = baseline_validation.get("verdict") if baseline_validation.get("valid") else "INCONCLUSIVE"
        breakfix_verdict = _breakfix_verdict(breakfix_validation, breakfix_records)
        fixed_verdict = _matrix_verdict(fixed_records)
        baseline_case_root = baseline_root / case_id
        breakfix_case_root = breakfix_root / case_id
        write_json(baseline_case_root / "agent-validation.json", baseline_validation)
        write_json(baseline_case_root / "replay-metadata.json", baseline_replay or {"load_error": baseline_error})
        write_json(baseline_case_root / "trajectory.json", {
            "lane": "phase2a-direct-provider-baseline",
            "provider": baseline_replay.get("provider") if baseline_replay else None,
            "model": baseline_replay.get("model") if baseline_replay else None,
            "instructions": {"prompt_file": "docs/phase2a-prompts.md", "prompt_id": baseline_replay.get("prompt_id") if baseline_replay else None, "workspace": str(case_root)},
            "context": baseline_replay.get("context") if baseline_replay else None,
            "structured_agent_result": baseline_validation,
            "tool_actions": baseline_replay.get("tool_actions", []) if baseline_replay else [],
            "retries": baseline_replay.get("retries", 0) if baseline_replay else 0,
            "parse_or_load_failure": baseline_error,
            "final_conclusion": baseline_validation.get("parsed") if baseline_validation.get("valid") else None,
            "ground_truth_supplied_to_agent": False,
        })
        write_text(baseline_case_root / "response.txt", baseline_replay.get("response_text", "") if baseline_replay else "")
        write_json(breakfix_case_root / "agent-validation.json", breakfix_validation)
        write_json(breakfix_case_root / "replay-metadata.json", breakfix_replay or {"load_error": breakfix_error})
        write_json(breakfix_case_root / "trajectory.json", {
            "lane": "phase2a-direct-provider-breakfix",
            "provider": breakfix_replay.get("provider") if breakfix_replay else None,
            "model": breakfix_replay.get("model") if breakfix_replay else None,
            "instructions": {"prompt_file": "docs/phase2a-prompts.md", "prompt_id": breakfix_replay.get("prompt_id") if breakfix_replay else None, "workspace": str(case_root)},
            "context": breakfix_replay.get("context") if breakfix_replay else None,
            "structured_agent_result": breakfix_validation,
            "tool_actions": breakfix_replay.get("tool_actions", []) if breakfix_replay else [],
            "retries": breakfix_replay.get("retries", 0) if breakfix_replay else 0,
            "parse_or_load_failure": breakfix_error,
            "final_conclusion": breakfix_validation.get("parsed") if breakfix_validation.get("valid") else None,
            "ground_truth_supplied_to_agent": False,
            "execution_decides_success": True,
        })
        write_text(breakfix_case_root / "response.txt", breakfix_replay.get("response_text", "") if breakfix_replay else "")
        write_json(breakfix_case_root / "proposed-experiments.json", {
            "selected_supported_ids": selected,
            "unsupported_assumptions": breakfix_validation.get("unsupported_assumptions", []),
            "supported_catalogue": [experiment.id for experiment in EXPERIMENTS],
        })

        baseline_confirmed = []
        breakfix_confirmed = [record["experiment_id"] for record in breakfix_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"]
        fixed_confirmed = [record["experiment_id"] for record in fixed_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"]
        comparison["cases"].append({
            "id": case_id,
            "title": public["title"],
            "surface": public["surface"],
            "diff_path": _relative(root, case_root / "after" / "app.py"),
            "visible_tests": visible.as_dict(),
            "baseline": {
                "valid_response": baseline_validation.get("valid", False),
                "verdict": baseline_verdict,
                "findings": baseline_validation.get("findings", []),
                "model_runtime_ms": baseline_replay.get("runtime_ms") if baseline_replay else None,
                "model_calls": baseline_replay.get("model_calls", 1) if baseline_replay else 0,
                "trajectory_path": _relative(root, baseline_case_root / "trajectory.json"),
            },
            "fixed_matrix": {
                "verdict": fixed_verdict,
                "experiments_run": len(fixed_records),
                "confirmed_experiments": fixed_confirmed,
                "cleared_experiments": [record["experiment_id"] for record in fixed_records if record["evaluation"]["evidence_state"] == "CLEARED"],
                "unsupported_experiments": [record["experiment_id"] for record in fixed_records if record["evaluation"]["evidence_state"] == "UNSUPPORTED"],
                "execution_runtime_ms": sum(record["duration_ms"] for record in fixed_records),
                "complete_confirmed_experiments": sum(record["evaluation"]["evidence_complete"] for record in fixed_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"),
                "evidence_path": _relative(root, fixed_root / case_id),
            },
            "breakfix": {
                "valid_response": breakfix_validation.get("valid", False),
                "verdict": breakfix_verdict,
                "assumptions": breakfix_validation.get("assumptions", []),
                "unsupported_assumptions": breakfix_validation.get("unsupported_assumptions", []),
                "experiments_selected": selected,
                "experiments_run": len(breakfix_records),
                "confirmed_experiments": breakfix_confirmed,
                "cleared_experiments": [record["experiment_id"] for record in breakfix_records if record["evaluation"]["evidence_state"] == "CLEARED"],
                "inconclusive_experiments": [record["experiment_id"] for record in breakfix_records if record["evaluation"]["evidence_state"] == "INCONCLUSIVE"],
                "model_runtime_ms": breakfix_replay.get("runtime_ms") if breakfix_replay else None,
                "model_calls": breakfix_replay.get("model_calls", 1) if breakfix_replay else 0,
                "execution_runtime_ms": sum(record["duration_ms"] for record in breakfix_records),
                "complete_confirmed_experiments": sum(record["evaluation"]["evidence_complete"] for record in breakfix_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"),
                "trajectory_path": _relative(root, breakfix_case_root / "trajectory.json"),
                "evidence_path": _relative(root, breakfix_case_root),
            },
            "truth_for_evaluator": truth,
        })

    # Truth is copied only into the evaluator output, never into prompts or trajectories.
    for lane in ("baseline", "fixed_matrix", "breakfix"):
        comparison.setdefault("metrics", {})[lane] = _lane_metrics(
            [{**case, "fault": bool(truth_by_case[case["id"]].get("fault"))} for case in comparison["cases"]], lane
        )
        comparison.setdefault("confusion_matrices", {})[lane] = _confusion_matrix(
            [{**case, "fault": bool(truth_by_case[case["id"]].get("fault"))} for case in comparison["cases"]], lane
        )
    comparison["model"] = {
        "baseline": _metadata(baseline_replays),
        "breakfix": _metadata(breakfix_replays),
        "same_provider": _metadata(baseline_replays).get("provider") == _metadata(breakfix_replays).get("provider"),
        "same_model": _metadata(baseline_replays).get("model") == _metadata(breakfix_replays).get("model"),
        "telemetry_available": all(all(replay.get(field) is not None for field in ("input_tokens", "output_tokens", "latency_ms", "monetary_cost_usd")) for replay in baseline_replays + breakfix_replays),
    }
    comparison["integrity"]["same_model_metadata_for_agent_lanes"] = bool(comparison["model"]["same_provider"] and comparison["model"]["same_model"])
    comparison["protocol"] = {
        "path": "docs/phase2a-evaluation-protocol.md",
        "primary_metric": "evidence-backed correct verdict rate",
        "fixed_matrix_experiments_per_case": len(EXPERIMENTS),
        "efficiency_threshold_matrix_fraction": 0.5,
        "efficiency_threshold_experiments_per_confirmed_defect": 3.0,
    }
    write_json(evidence_root / "comparison.json", comparison)
    write_text(evidence_root / "stdout.log", json.dumps(comparison, indent=2) + "\n")
    write_text(evidence_root / "stderr.log", "")
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the frozen Phase 2A holdout from captured model replays.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = run_phase2a(args.root)
    print(f"Run: {result['run_id']}")
    for lane in ("baseline", "fixed_matrix", "breakfix"):
        metrics = result["metrics"][lane]
        print(f"{lane}: correct={metrics['correct_verdict_rate']!s} fault_recall={metrics['fault_recall']!s} experiments={metrics['experiments_executed']}")
    print(f"Evidence: evidence/{result['run_id']}")


if __name__ == "__main__":
    main()
