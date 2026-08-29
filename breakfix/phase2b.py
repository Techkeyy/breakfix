from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_contract import validate_phase2b_baseline_response, validate_phase2b_breakfix_response
from .diffing import make_diff
from .evidence import write_json, write_text
from .executor import run_experiment, run_visible_tests
from .experiments import EXPERIMENTS, experiment_by_id, payload_for


PHASE2B_CASE_IDS = ("xq7", "m2v", "r9c", "k4d", "p6h", "w1s", "b8n", "z3f", "u5j", "e0r", "a6t", "d1y", "g8p", "n4k", "s2m", "v7c")
PHASE2B_MAX_EXPERIMENTS = 3


def holdout_case_dir(root: Path, case_id: str) -> Path:
    return root / "benchmark" / "phase2b_holdout" / case_id


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_truth(root: Path) -> dict[str, Any]:
    configured = os.environ.get("BREAKFIX_PHASE2B_TRUTH_PATH")
    path = Path(configured) if configured else root.parent / "BreakFix-private" / "phase2b_ground_truth.json"
    if not path.exists():
        raise RuntimeError("Phase 2B evaluator requires an external private truth file: set BREAKFIX_PHASE2B_TRUTH_PATH")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_replay(root: Path, lane: str, case_id: str) -> tuple[dict[str, Any] | None, str | None]:
    path = root / "trajectories" / "phase2b" / lane / case_id / "replay.json"
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
        "api_errors": sum(1 for replay in replays if replay.get("api_error")),
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
        and isinstance(execution.get("payload"), dict)
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


def _record_execution(lane_dir: Path, case_id: str, experiment_id: str, execution: Any, evaluation: dict[str, Any], payload: dict[str, Any]) -> None:
    target = lane_dir / case_id / "execution" / experiment_id
    write_json(target / "result.json", {**execution.as_dict(), "payload": payload, "evaluation": evaluation})
    write_text(target / "stdout.log", execution.stdout)
    write_text(target / "stderr.log", execution.stderr)


def _select_experiments(validation: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    if not validation.get("valid"):
        return [], []
    selected: list[str] = []
    unsupported = list(validation.get("unsupported_assumptions", []))
    for assumption in validation.get("assumptions", []):
        proposed = assumption.get("proposed_experiment", {})
        experiment_id = proposed.get("id") if isinstance(proposed, dict) else None
        if experiment_id not in {experiment.id for experiment in EXPERIMENTS}:
            continue
        if experiment_id not in selected and len(selected) < PHASE2B_MAX_EXPERIMENTS:
            selected.append(experiment_id)
    return selected, unsupported


def _targeted_outcome(validation: dict[str, Any], records: list[dict[str, Any]], api_error: str | None = None) -> str:
    if api_error or not validation.get("valid"):
        return "ERROR"
    if any(record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK" for record in records):
        return "CONFIRMED BREAK"
    oracle_records = [record for record in records if record["evaluation"]["evidence_state"] != "UNSUPPORTED"]
    if oracle_records and all(record["evaluation"]["evidence_state"] == "CLEARED" for record in oracle_records):
        return "NO BREAK CONFIRMED"
    if not oracle_records:
        return "UNSUPPORTED"
    return "ERROR"


def _matrix_outcome(records: list[dict[str, Any]]) -> str:
    if any(record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK" for record in records):
        return "CONFIRMED BREAK"
    oracle_records = [record for record in records if record["evaluation"]["evidence_state"] != "UNSUPPORTED"]
    if oracle_records and all(record["evaluation"]["evidence_state"] == "CLEARED" for record in oracle_records):
        return "NO BREAK CONFIRMED"
    if not oracle_records:
        return "UNSUPPORTED"
    return "ERROR"


def _execution_metrics(cases: list[dict[str, Any]], lane: str) -> dict[str, Any]:
    faults = [case for case in cases if case["fault"]]
    safe = [case for case in cases if not case["fault"]]
    outcomes = [case[lane]["outcome"] for case in cases]
    confirmed_faults = [case for case in faults if case[lane]["outcome"] == "CONFIRMED BREAK"]
    false_confirmed = [case for case in safe if case[lane]["outcome"] == "CONFIRMED BREAK"]
    confirmed_experiments = sum(len(case[lane].get("confirmed_experiments", [])) for case in cases)
    complete_evidence = sum(case[lane].get("complete_confirmed_experiments", 0) for case in cases)
    executed = sum(case[lane].get("experiments_run", 0) for case in cases)
    return {
        "cases_total": len(cases),
        "fault_cases": len(faults),
        "safe_cases": len(safe),
        "seeded_fault_recall": len(confirmed_faults) / len(faults) if faults else None,
        "false_confirmed_breaks": len(false_confirmed),
        "false_confirmed_break_rate": len(false_confirmed) / len(safe) if safe else None,
        "total_experiments": executed,
        "confirmed_breaks": confirmed_experiments,
        "experiments_per_confirmed_defect": executed / confirmed_experiments if confirmed_experiments else None,
        "runtime_ms": sum(case[lane].get("execution_runtime_ms", 0) for case in cases),
        "executable_reproduction_rate": complete_evidence / confirmed_experiments if confirmed_experiments else None,
        "unsupported_assumptions": sum(len(case[lane].get("unsupported_assumptions", [])) for case in cases),
        "unsupported_assumption_rate": sum(bool(case[lane].get("unsupported_assumptions")) for case in cases) / len(cases) if cases else None,
        "no_break_confirmed_rate": outcomes.count("NO BREAK CONFIRMED") / len(cases) if cases else None,
        "tool_runtime_failures": outcomes.count("ERROR"),
        "tool_runtime_failure_rate": outcomes.count("ERROR") / len(cases) if cases else None,
        "outcome_counts": {outcome: outcomes.count(outcome) for outcome in sorted(set(outcomes))},
    }


def _baseline_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    faults = [case for case in cases if case["fault"]]
    safe = [case for case in cases if not case["fault"]]
    recommendations = [case["baseline"]["recommendation"] for case in cases]
    return {
        "cases_total": len(cases),
        "fault_cases": len(faults),
        "safe_cases": len(safe),
        "fault_identification_recall": sum(case["baseline"]["recommendation"] == "POTENTIAL_BREAK" for case in faults) / len(faults) if faults else None,
        "safe_no_break_specificity": sum(case["baseline"]["recommendation"] == "NO_BREAK_FOUND" for case in safe) / len(safe) if safe else None,
        "potential_break_warnings": sum(case["baseline"]["recommendation"] == "POTENTIAL_BREAK" for case in safe),
        "recommendation_counts": {value: recommendations.count(value) for value in sorted(set(recommendations))},
        "model_calls": sum(case["baseline"].get("model_calls", 0) for case in cases),
    }


def _confusion_matrix(cases: list[dict[str, Any]], lane: str) -> dict[str, int]:
    return {
        "fault_as_confirmed_break": sum(case["fault"] and case[lane]["outcome"] == "CONFIRMED BREAK" for case in cases),
        "fault_as_no_break_confirmed": sum(case["fault"] and case[lane]["outcome"] == "NO BREAK CONFIRMED" for case in cases),
        "fault_as_unsupported": sum(case["fault"] and case[lane]["outcome"] == "UNSUPPORTED" for case in cases),
        "fault_as_error": sum(case["fault"] and case[lane]["outcome"] == "ERROR" for case in cases),
        "safe_as_confirmed_break": sum((not case["fault"]) and case[lane]["outcome"] == "CONFIRMED BREAK" for case in cases),
        "safe_as_no_break_confirmed": sum((not case["fault"]) and case[lane]["outcome"] == "NO BREAK CONFIRMED" for case in cases),
        "safe_as_unsupported": sum((not case["fault"]) and case[lane]["outcome"] == "UNSUPPORTED" for case in cases),
        "safe_as_error": sum((not case["fault"]) and case[lane]["outcome"] == "ERROR" for case in cases),
    }


def _public_case_record(case: dict[str, Any]) -> dict[str, Any]:
    """Remove evaluator-only truth before comparison evidence is persisted."""
    return {key: value for key, value in case.items() if key not in {"surface", "fault", "truth_for_evaluator"}}


def run_phase2b(root: Path) -> dict[str, Any]:
    root = root.resolve()
    truth_by_case = _load_truth(root)
    run_id = "phase2b-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root = root / "evidence" / run_id
    baseline_root = evidence_root / "baseline"
    fixed_root = evidence_root / "fixed-matrix"
    breakfix_root = evidence_root / "breakfix"
    comparison: dict[str, Any] = {
        "run_id": run_id,
        "phase": "2B-evidence-efficient-break-confirmation",
        "holdout": "benchmark/phase2b_holdout",
        "cases": [],
        "integrity": {
            "fresh_holdout": True,
            "previous_phase_cases_used_as_primary_evidence": False,
            "ground_truth_used_by_evaluator_only": True,
            "real_subprocess_executions": True,
            "fixed_matrix_complete_catalogue": True,
            "breakfix_budget": PHASE2B_MAX_EXPERIMENTS,
        },
    }
    baseline_replays: list[dict[str, Any]] = []
    breakfix_replays: list[dict[str, Any]] = []

    for case_id in PHASE2B_CASE_IDS:
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
        baseline_validation = validate_phase2b_baseline_response(baseline_replay["response_text"]) if baseline_replay else {"valid": False, "validation_failures": [baseline_error], "recommendation": None, "findings": []}
        breakfix_validation = validate_phase2b_breakfix_response(breakfix_replay["response_text"]) if breakfix_replay else {"valid": False, "validation_failures": [breakfix_error], "assumptions": [], "unsupported_assumptions": []}

        fixed_records: list[dict[str, Any]] = []
        for experiment in EXPERIMENTS:
            payload = payload_for(experiment)
            execution = run_experiment(case_root / "after", experiment.id, payload)
            execution_dict = {**execution.as_dict(), "payload": payload}
            evaluation = _evaluate_execution(truth, experiment.id, execution_dict)
            _record_execution(fixed_root, case_id, experiment.id, execution, evaluation, payload)
            fixed_records.append({**execution_dict, "evaluation": evaluation})

        selected, unsupported = _select_experiments(breakfix_validation)
        breakfix_records: list[dict[str, Any]] = []
        for experiment_id in selected:
            experiment = experiment_by_id(experiment_id)
            payload = payload_for(experiment)
            execution = run_experiment(case_root / "after", experiment.id, payload)
            execution_dict = {**execution.as_dict(), "payload": payload}
            evaluation = _evaluate_execution(truth, experiment.id, execution_dict)
            _record_execution(breakfix_root, case_id, experiment.id, execution, evaluation, payload)
            breakfix_records.append({**execution_dict, "evaluation": evaluation})
            if evaluation["evidence_state"] == "CONFIRMED_BREAK":
                break

        baseline_recommendation = baseline_validation.get("recommendation") if baseline_validation.get("valid") else "INCONCLUSIVE"
        baseline_case_root = baseline_root / case_id
        breakfix_case_root = breakfix_root / case_id
        write_json(baseline_case_root / "agent-validation.json", baseline_validation)
        write_json(baseline_case_root / "replay-metadata.json", baseline_replay or {"load_error": baseline_error})
        write_json(baseline_case_root / "trajectory.json", {"lane": "phase2b-direct-provider-baseline", "provider": baseline_replay.get("provider") if baseline_replay else None, "model": baseline_replay.get("model") if baseline_replay else None, "instructions": {"prompt_file": "docs/phase2b-prompts.md", "prompt_id": baseline_replay.get("prompt_id") if baseline_replay else None}, "context": baseline_replay.get("prompt_context") if baseline_replay else None, "structured_agent_result": baseline_validation, "tool_actions": baseline_replay.get("tool_actions", []) if baseline_replay else [], "retries": baseline_replay.get("retries", 0) if baseline_replay else 0, "parse_or_load_failure": baseline_error, "final_conclusion": baseline_validation.get("parsed") if baseline_validation.get("valid") else None, "ground_truth_supplied_to_agent": False})
        write_text(baseline_case_root / "response.txt", baseline_replay.get("response_text", "") if baseline_replay else "")
        write_json(breakfix_case_root / "agent-validation.json", breakfix_validation)
        write_json(breakfix_case_root / "replay-metadata.json", breakfix_replay or {"load_error": breakfix_error})
        write_json(breakfix_case_root / "trajectory.json", {"lane": "phase2b-direct-provider-breakfix", "provider": breakfix_replay.get("provider") if breakfix_replay else None, "model": breakfix_replay.get("model") if breakfix_replay else None, "instructions": {"prompt_file": "docs/phase2b-prompts.md", "prompt_id": breakfix_replay.get("prompt_id") if breakfix_replay else None, "budget": PHASE2B_MAX_EXPERIMENTS}, "context": breakfix_replay.get("prompt_context") if breakfix_replay else None, "structured_agent_result": breakfix_validation, "tool_actions": breakfix_replay.get("tool_actions", []) if breakfix_replay else [], "retries": breakfix_replay.get("retries", 0) if breakfix_replay else 0, "parse_or_load_failure": breakfix_error, "final_conclusion": breakfix_validation.get("parsed") if breakfix_validation.get("valid") else None, "ground_truth_supplied_to_agent": False, "execution_decides_success": True})
        write_text(breakfix_case_root / "response.txt", breakfix_replay.get("response_text", "") if breakfix_replay else "")
        write_json(breakfix_case_root / "selection.json", {"selected_supported_ids": selected, "unsupported_assumptions": unsupported, "max_experiments": PHASE2B_MAX_EXPERIMENTS, "supported_catalogue": [experiment.id for experiment in EXPERIMENTS]})

        fixed_confirmed = [record["experiment_id"] for record in fixed_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"]
        breakfix_confirmed = [record["experiment_id"] for record in breakfix_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"]
        breakfix_outcome = _targeted_outcome(breakfix_validation, breakfix_records, breakfix_replay.get("api_error") if breakfix_replay else None)
        comparison["cases"].append({
            "id": case_id,
            "title": public["title"],
            "surface": truth.get("surface"),
            "task": public["task"],
            "diff": diff,
            "diff_path": _relative(root, case_root / "after" / "app.py"),
            "visible_tests": visible.as_dict(),
            "baseline": {"recommendation": baseline_recommendation, "valid_response": baseline_validation.get("valid", False), "findings": baseline_validation.get("findings", []), "model_calls": baseline_replay.get("model_calls", 0) if baseline_replay else 0, "trajectory_path": _relative(root, baseline_case_root / "trajectory.json")},
            "fixed_matrix": {"outcome": _matrix_outcome(fixed_records), "experiments_run": len(fixed_records), "confirmed_experiments": fixed_confirmed, "execution_runtime_ms": sum(record["duration_ms"] for record in fixed_records), "complete_confirmed_experiments": sum(record["evaluation"]["evidence_complete"] for record in fixed_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"), "evidence_path": _relative(root, fixed_root / case_id)},
            "breakfix": {"outcome": breakfix_outcome, "valid_response": breakfix_validation.get("valid", False), "assumptions": breakfix_validation.get("assumptions", []), "unsupported_assumptions": unsupported, "experiments_selected": selected, "experiments_run": len(breakfix_records), "confirmed_experiments": breakfix_confirmed, "execution_runtime_ms": sum(record["duration_ms"] for record in breakfix_records), "complete_confirmed_experiments": sum(record["evaluation"]["evidence_complete"] for record in breakfix_records if record["evaluation"]["evidence_state"] == "CONFIRMED_BREAK"), "trajectory_path": _relative(root, breakfix_case_root / "trajectory.json"), "evidence_path": _relative(root, breakfix_case_root)},
            "fault": bool(truth.get("fault")),
            "truth_for_evaluator": truth,
        })

    for lane in ("fixed_matrix", "breakfix"):
        comparison.setdefault("metrics", {})[lane] = _execution_metrics(comparison["cases"], lane)
        comparison.setdefault("confusion_matrices", {})[lane] = _confusion_matrix(comparison["cases"], lane)
    comparison.setdefault("metrics", {})["baseline"] = _baseline_metrics(comparison["cases"])
    baseline_meta = _metadata(baseline_replays)
    breakfix_meta = _metadata(breakfix_replays)
    comparison["model"] = {"baseline": baseline_meta, "breakfix": breakfix_meta, "same_provider": baseline_meta.get("provider") == breakfix_meta.get("provider"), "same_model": baseline_meta.get("model") == breakfix_meta.get("model"), "telemetry_available": all(all(replay.get(field) is not None for field in ("input_tokens", "output_tokens", "latency_ms", "monetary_cost_usd")) and not replay.get("api_error") for replay in baseline_replays + breakfix_replays), "direct_provider_required": True}
    fixed_count = comparison["metrics"]["fixed_matrix"]["total_experiments"]
    breakfix_metrics = comparison["metrics"]["breakfix"]
    eligible = bool(breakfix_metrics["seeded_fault_recall"] == 1.0 and breakfix_metrics["false_confirmed_breaks"] == 0 and breakfix_metrics["tool_runtime_failures"] == 0 and comparison["model"]["telemetry_available"])
    comparison["primary_metric"] = {"name": "total experiments required for complete seeded-fault recall with zero false confirmed breaks", "eligible": eligible, "value": breakfix_metrics["total_experiments"] if eligible else None, "observed_breakfix_experiments": breakfix_metrics["total_experiments"], "fixed_matrix_experiments": fixed_count, "experiment_reduction_percentage": (fixed_count - breakfix_metrics["total_experiments"]) / fixed_count * 100 if fixed_count else None, "frozen_fault_recall_requirement": "8/8", "frozen_false_confirmed_break_requirement": "0/8"}
    comparison["protocol"] = {"path": "docs/phase2b-evaluation-protocol.md", "primary_metric_frozen": True, "budget_per_case": PHASE2B_MAX_EXPERIMENTS, "fixed_matrix_policy": "all 8 supported experiments once per case"}
    comparison["cases"] = [_public_case_record(case) for case in comparison["cases"]]
    write_json(evidence_root / "comparison.json", comparison)
    write_text(evidence_root / "stdout.log", json.dumps(comparison, indent=2) + "\n")
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the frozen Phase 2B holdout from direct-provider replays.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = run_phase2b(args.root)
    print(json.dumps({"run_id": result["run_id"], "primary_metric": result["primary_metric"], "metrics": result["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
