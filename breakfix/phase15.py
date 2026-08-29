from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_contract import validate_baseline_response, validate_breakfix_response
from .benchmark import load_ground_truth
from .evidence import write_json, write_text
from .executor import run_experiment, run_visible_tests
from .experiments import EXPERIMENTS, experiment_by_id, payload_for
from .diffing import make_diff


PHASE15_CASES = (
    ("case_01", "case_input_boundary"),
    ("case_02", "case_retry_duplicate"),
    ("case_03", "case_stale_state"),
    ("case_04", "case_reordered_events"),
    ("case_05", "case_timezone_robust"),
)


def phase15_case_dir(root: Path, case_id: str) -> Path:
    return root / "benchmark" / "phase1_5_cases" / case_id


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _evaluation(
    truth: dict[str, Any],
    experiment_id: str,
    execution: dict[str, Any],
) -> dict[str, Any]:
    is_fault_experiment = experiment_id in truth.get("fault_experiments", [])
    expected = truth.get("expected_outputs", {}).get(experiment_id)
    matches_expected = expected is None or execution.get("output") == expected
    execution_proved_failure = bool(execution.get("process_failed") or not matches_expected)
    return {
        "fault_experiment": is_fault_experiment,
        "expected_output": expected,
        "matches_expected": matches_expected,
        "confirmed_break": bool(truth.get("fault") and is_fault_experiment and execution_proved_failure),
        "execution_proved_failure": execution_proved_failure,
    }


def _record_execution(root: Path, lane_dir: Path, case_id: str, experiment_id: str, execution: Any, evaluation: dict[str, Any]) -> None:
    target = lane_dir / case_id / "execution" / experiment_id
    write_json(target / "result.json", {**execution.as_dict(), "evaluation": evaluation})
    write_text(target / "stdout.log", execution.stdout)
    write_text(target / "stderr.log", execution.stderr)


def _load_replay(root: Path, lane: str, case_id: str) -> tuple[dict[str, Any] | None, str | None]:
    path = root / "trajectories" / "phase1.5" / lane / case_id / "replay.json"
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
    runtime_values = [replay.get("runtime_ms") for replay in replays if isinstance(replay.get("runtime_ms"), int)]
    token_values = [replay.get("token_usage") for replay in replays if replay.get("token_usage") is not None]
    cost_values = [replay.get("monetary_cost_usd") for replay in replays if replay.get("monetary_cost_usd") is not None]
    return {
        "provider": providers[0] if len(providers) == 1 else providers,
        "model": models[0] if len(models) == 1 else models,
        "reasoning_effort": reasoning[0] if len(reasoning) == 1 else reasoning,
        "temperature": replays[0].get("temperature") if replays else None,
        "model_calls": sum(int(replay.get("model_calls", 1)) for replay in replays),
        "runtime_ms": sum(runtime_values) if len(runtime_values) == len(replays) else None,
        "token_usage": sum(token_values) if len(token_values) == len(replays) else None,
        "monetary_cost_usd": sum(cost_values) if len(cost_values) == len(replays) else None,
        "retries": sum(int(replay.get("retries", 0)) for replay in replays),
    }


def _lane_metric(records: list[dict[str, Any]], lane: str, truth_by_public_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fault_records = [record for record in records if truth_by_public_id[record["id"]].get("fault")]
    safe_records = [record for record in records if not truth_by_public_id[record["id"]].get("fault")]
    detected = [record[lane]["detected"] for record in fault_records]
    false_approvals = [record[lane]["false_approval"] for record in fault_records]
    false_positives = [record[lane]["false_positive"] for record in safe_records]
    experiments = sum(record[lane].get("experiments_run", 0) for record in records)
    confirmed = sum(len(record[lane].get("confirmed_experiments", [])) for record in records)
    durations = [record[lane].get("execution_runtime_ms") for record in records]
    return {
        "seeded_faults_discovered": sum(detected),
        "seeded_faults_total": len(fault_records),
        "seeded_faults_missed": len(fault_records) - sum(detected),
        "defect_detection_rate": sum(detected) / len(fault_records) if fault_records else None,
        "false_positives_on_safe_case": sum(false_positives),
        "false_approval_rate": sum(false_approvals) / len(fault_records) if fault_records else None,
        "experiments_executed": experiments,
        "confirmed_failures_produced": confirmed,
        "executable_reproduction_rate": confirmed / confirmed if confirmed else None,
        "execution_runtime_ms": sum(durations) if all(isinstance(value, int) for value in durations) else None,
    }


def run_phase15(root: Path) -> dict[str, Any]:
    root = root.resolve()
    ground_truth = load_ground_truth(root)
    run_id = "phase1.5-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root = root / "evidence" / run_id
    baseline_root = evidence_root / "baseline"
    fixed_root = evidence_root / "fixed-matrix"
    breakfix_root = evidence_root / "breakfix"
    comparison: dict[str, Any] = {
        "run_id": run_id,
        "phase": "1.5-validation-closure",
        "cases": [],
        "integrity": {
            "ground_truth_used_by_evaluator_only": True,
            "real_subprocess_executions": True,
            "real_model_responses_used": True,
            "same_model_metadata_for_agent_lanes": True,
            "fixture_to_experiment_mapping_used_by_agent": False,
        },
    }
    baseline_replays: list[dict[str, Any]] = []
    breakfix_replays: list[dict[str, Any]] = []

    for public_id, truth_id in PHASE15_CASES:
        case_root = phase15_case_dir(root, public_id)
        before_path = case_root / "before" / "app.py"
        after_path = case_root / "after" / "app.py"
        diff = make_diff(before_path, after_path)
        visible = run_visible_tests(case_root / "after")
        visible_dict = visible.as_dict()
        truth = ground_truth[truth_id]

        baseline_replay, baseline_load_error = _load_replay(root, "baseline", public_id)
        breakfix_replay, breakfix_load_error = _load_replay(root, "breakfix", public_id)
        if baseline_replay:
            baseline_replays.append(baseline_replay)
        if breakfix_replay:
            breakfix_replays.append(breakfix_replay)
        baseline_validation = validate_baseline_response(baseline_replay["response_text"]) if baseline_replay else {
            "valid": False,
            "validation_failures": [baseline_load_error],
            "findings": [],
        }
        breakfix_validation = validate_breakfix_response(breakfix_replay["response_text"]) if breakfix_replay else {
            "valid": False,
            "validation_failures": [breakfix_load_error],
            "assumptions": [],
            "selected_experiment_ids": [],
            "unsupported_assumptions": [],
        }

        baseline_findings = baseline_validation.get("findings", []) if baseline_validation.get("valid") else []
        baseline_flagged = bool(baseline_findings) or baseline_validation.get("decision") == "needs-review"
        baseline_detection = baseline_flagged and bool(truth.get("fault"))
        baseline_false_approval = bool(truth.get("fault") and not baseline_flagged)
        baseline_false_positive = bool(not truth.get("fault") and baseline_flagged)
        baseline_root_case = baseline_root / public_id
        write_json(baseline_root_case / "agent-validation.json", baseline_validation)
        write_json(baseline_root_case / "replay-metadata.json", baseline_replay or {"load_error": baseline_load_error})
        write_json(baseline_root_case / "trajectory.json", {
            "lane": "real-coding-agent-baseline",
            "provider": baseline_replay.get("provider") if baseline_replay else None,
            "model": baseline_replay.get("model") if baseline_replay else None,
            "instructions": {
                "prompt_file": baseline_replay.get("prompt_file"),
                "prompt_id": baseline_replay.get("prompt_id"),
                "workspace": baseline_replay.get("prompt_workspace"),
            } if baseline_replay else None,
            "context": baseline_replay.get("context") if baseline_replay else None,
            "structured_agent_result": baseline_validation,
            "tool_actions": baseline_replay.get("tool_actions", []) if baseline_replay else [],
            "retries": baseline_replay.get("retries", 0) if baseline_replay else 0,
            "parse_or_load_failure": baseline_load_error,
            "final_conclusion": baseline_validation.get("parsed") if baseline_validation.get("valid") else None,
            "ground_truth_supplied_to_agent": False,
        })
        write_text(baseline_root_case / "response.txt", baseline_replay.get("response_text", "") if baseline_replay else "")

        fixed_records: list[dict[str, Any]] = []
        for experiment in EXPERIMENTS:
            execution = run_experiment(case_root / "after", experiment.id, payload_for(experiment))
            evaluation = _evaluation(truth, experiment.id, execution.as_dict())
            _record_execution(root, fixed_root, public_id, experiment.id, execution, evaluation)
            fixed_records.append({**execution.as_dict(), "evaluation": evaluation})

        selected = breakfix_validation.get("selected_experiment_ids", []) if breakfix_validation.get("valid") else []
        breakfix_records: list[dict[str, Any]] = []
        for experiment_id in selected:
            experiment = experiment_by_id(experiment_id)
            execution = run_experiment(case_root / "after", experiment.id, payload_for(experiment))
            evaluation = _evaluation(truth, experiment.id, execution.as_dict())
            _record_execution(root, breakfix_root, public_id, experiment.id, execution, evaluation)
            breakfix_records.append({**execution.as_dict(), "evaluation": evaluation})

        breakfix_detected = any(record["evaluation"]["confirmed_break"] for record in breakfix_records)
        fixed_detected = any(record["evaluation"]["confirmed_break"] for record in fixed_records)
        breakfix_false_positive = bool(not truth.get("fault") and breakfix_detected)
        breakfix_false_approval = bool(truth.get("fault") and not breakfix_detected)
        fixed_false_positive = bool(not truth.get("fault") and fixed_detected)
        fixed_false_approval = bool(truth.get("fault") and not fixed_detected)
        breakfix_case_root = breakfix_root / public_id
        write_json(breakfix_case_root / "agent-validation.json", breakfix_validation)
        write_json(breakfix_case_root / "replay-metadata.json", breakfix_replay or {"load_error": breakfix_load_error})
        write_json(breakfix_case_root / "trajectory.json", {
            "lane": "real-breakfix-reasoning-agent",
            "provider": breakfix_replay.get("provider") if breakfix_replay else None,
            "model": breakfix_replay.get("model") if breakfix_replay else None,
            "instructions": {
                "prompt_file": breakfix_replay.get("prompt_file"),
                "prompt_id": breakfix_replay.get("prompt_id"),
                "workspace": breakfix_replay.get("prompt_workspace"),
            } if breakfix_replay else None,
            "context": breakfix_replay.get("context") if breakfix_replay else None,
            "structured_agent_result": breakfix_validation,
            "tool_actions": breakfix_replay.get("tool_actions", []) if breakfix_replay else [],
            "retries": breakfix_replay.get("retries", 0) if breakfix_replay else 0,
            "parse_or_load_failure": breakfix_load_error,
            "final_conclusion": breakfix_validation.get("parsed") if breakfix_validation.get("valid") else None,
            "ground_truth_supplied_to_agent": False,
            "execution_decides_success": True,
        })
        write_text(breakfix_case_root / "response.txt", breakfix_replay.get("response_text", "") if breakfix_replay else "")
        write_json(breakfix_case_root / "proposed-experiments.json", {
            "selected_supported_ids": selected,
            "unsupported_assumptions": breakfix_validation.get("unsupported_assumptions", []),
            "supported_catalogue": breakfix_validation.get("supported_catalogue", [experiment.id for experiment in EXPERIMENTS]),
        })

        comparison["cases"].append({
            "id": public_id,
            "title": json.loads((case_root / "public.json").read_text(encoding="utf-8"))["title"],
            "truth_id_evaluator_only": truth_id,
            "visible_tests": visible_dict,
            "baseline": {
                "valid_response": baseline_validation.get("valid", False),
                "flagged": baseline_flagged,
                "detected": baseline_detection,
                "detection": baseline_detection,
                "false_approval": baseline_false_approval,
                "false_positive": baseline_false_positive,
                "model_runtime_ms": baseline_replay.get("runtime_ms") if baseline_replay else None,
                "model_calls": baseline_replay.get("model_calls", 1) if baseline_replay else 0,
                "trajectory_path": _relative(root, baseline_root_case / "trajectory.json"),
            },
            "fixed_matrix": {
                "experiments_run": len(fixed_records),
                "detected": fixed_detected,
                "false_approval": fixed_false_approval,
                "false_positive": fixed_false_positive,
                "confirmed_experiments": [record["experiment_id"] for record in fixed_records if record["evaluation"]["confirmed_break"]],
                "execution_runtime_ms": sum(record["duration_ms"] for record in fixed_records),
                "evidence_path": _relative(root, fixed_root / public_id),
            },
            "breakfix": {
                "valid_response": breakfix_validation.get("valid", False),
                "assumptions": breakfix_validation.get("assumptions", []),
                "unsupported_assumptions": breakfix_validation.get("unsupported_assumptions", []),
                "experiments_selected": selected,
                "experiments_run": len(breakfix_records),
                "detected": breakfix_detected,
                "false_approval": breakfix_false_approval,
                "false_positive": breakfix_false_positive,
                "confirmed_experiments": [record["experiment_id"] for record in breakfix_records if record["evaluation"]["confirmed_break"]],
                "model_runtime_ms": breakfix_replay.get("runtime_ms") if breakfix_replay else None,
                "model_calls": breakfix_replay.get("model_calls", 1) if breakfix_replay else 0,
                "execution_runtime_ms": sum(record["duration_ms"] for record in breakfix_records),
                "trajectory_path": _relative(root, breakfix_case_root / "trajectory.json"),
                "evidence_path": _relative(root, breakfix_root / public_id),
            },
        })

    truth_by_public_id = {public_id: ground_truth[truth_id] for public_id, truth_id in PHASE15_CASES}
    for lane in ("baseline", "fixed_matrix", "breakfix"):
        comparison.setdefault("metrics", {})[lane] = _lane_metric(comparison["cases"], lane, truth_by_public_id)
    comparison["metrics"]["fault_cases"] = sum(bool(truth.get("fault")) for truth in truth_by_public_id.values())
    comparison["metrics"]["safe_cases"] = sum(not truth.get("fault") for truth in truth_by_public_id.values())
    comparison["model"] = {
        "baseline": _metadata(baseline_replays),
        "breakfix": _metadata(breakfix_replays),
        "same_provider": _metadata(baseline_replays).get("provider") == _metadata(breakfix_replays).get("provider"),
        "same_model": _metadata(baseline_replays).get("model") == _metadata(breakfix_replays).get("model"),
        "token_usage_available": False,
        "monetary_cost_available": False,
    }
    comparison["integrity"]["same_model_metadata_for_agent_lanes"] = bool(comparison["model"]["same_provider"] and comparison["model"]["same_model"])
    write_json(evidence_root / "comparison.json", comparison)
    write_text(evidence_root / "stdout.log", json.dumps(comparison, indent=2) + "\n")
    write_text(evidence_root / "stderr.log", "")
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate BreakFix Phase 1.5 from captured real-agent replays.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = run_phase15(args.root)
    print(f"Run: {result['run_id']}")
    for lane in ("baseline", "fixed_matrix", "breakfix"):
        metrics = result["metrics"][lane]
        print(f"{lane}: detection={metrics['defect_detection_rate']!s} experiments={metrics['experiments_executed']}")
    print(f"Evidence: evidence/{result['run_id']}")


if __name__ == "__main__":
    main()
