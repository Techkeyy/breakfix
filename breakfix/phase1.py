from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .baseline import review_change
from .benchmark import after_dir, case_dir, load_cases, load_ground_truth
from .diffing import make_diff
from .evidence import write_json, write_text
from .executor import run_experiment, run_visible_tests
from .experiments import EXPERIMENTS, experiment_by_id, payload_for
from .planner import infer_assumptions, targeted_experiments


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _evaluation(case_id: str, experiment_id: str, execution: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, Any]:
    case_truth = ground_truth[case_id]
    is_fault_experiment = experiment_id in case_truth.get("fault_experiments", [])
    expected = case_truth.get("expected_outputs", {}).get(experiment_id)
    matches_expected = expected is None or execution.get("output") == expected
    confirmed_break = bool(
        case_truth.get("fault")
        and is_fault_experiment
        and (execution.get("process_failed") or not matches_expected)
    )
    return {
        "fault_experiment": is_fault_experiment,
        "expected_output": expected,
        "matches_expected": matches_expected,
        "confirmed_break": confirmed_break,
        "execution_proved_failure": bool(execution.get("process_failed") or not matches_expected),
    }


def _record_execution(root: Path, lane_dir: Path, case_id: str, experiment_id: str, execution: Any, evaluation: dict[str, Any]) -> None:
    target = lane_dir / case_id / "execution" / experiment_id
    write_json(target / "result.json", {**execution.as_dict(), "evaluation": evaluation})
    write_text(target / "stdout.log", execution.stdout)
    write_text(target / "stderr.log", execution.stderr)


def run_phase1(root: Path) -> dict[str, Any]:
    root = root.resolve()
    cases = load_cases(root)
    ground_truth = load_ground_truth(root)
    run_id = "phase1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root = root / "evidence" / run_id
    fixed_root = evidence_root / "fixed-matrix"
    breakfix_root = evidence_root / "breakfix"
    baseline_root = evidence_root / "baseline"
    comparison: dict[str, Any] = {"run_id": run_id, "lanes": {}, "cases": []}

    for case in cases:
        case_id = case["id"]
        before_path = case_dir(root, case_id) / "before" / "app.py"
        after_path = case_dir(root, case_id) / "after" / "app.py"
        diff = make_diff(before_path, after_path)
        visible = run_visible_tests(after_dir(root, case_id))
        visible_dict = visible.as_dict()

        baseline_result = review_change(diff, visible_dict)
        baseline_case_root = baseline_root / case_id
        write_json(baseline_case_root / "result.json", baseline_result)
        write_json(
            baseline_case_root / "trajectory.json",
            {
                "agent": "generic-review-baseline",
                "instructions": "Review the selected change using only the diff, surrounding code, and provided tests. Do not invent hidden results.",
                "context": {"diff": diff, "visible_tests": visible_dict},
                "tool_calls": ["read_selected_diff", "read_visible_test_result"],
                "output": baseline_result,
            },
        )
        write_text(baseline_case_root / "stdout.log", json.dumps(baseline_result, indent=2) + "\n")
        write_text(baseline_case_root / "stderr.log", "")

        assumptions = infer_assumptions(diff)
        selected = targeted_experiments(assumptions)
        change_record = {
            "case_id": case_id,
            "selected_change": {
                "before": _relative(root, before_path),
                "after": _relative(root, after_path),
                "diff": diff,
            },
            "visible_tests": visible_dict,
        }
        write_json(breakfix_root / case_id / "change.json", change_record)
        write_json(
            breakfix_root / case_id / "assumptions.json",
            {
                "assumptions": [assumption.__dict__ for assumption in assumptions],
                "ground_truth_supplied_to_agent": False,
            },
        )
        write_json(
            breakfix_root / case_id / "experiments.json",
            {
                "selected": [
                    {
                        "id": experiment_id,
                        "description": experiment_by_id(experiment_id).description,
                        "why": next(
                            (
                                assumption.statement
                                for assumption in assumptions
                                if experiment_id in assumption.selected_experiments
                            ),
                            "Selected by ranked assumption evidence.",
                        ),
                    }
                    for experiment_id in selected
                ],
                "available_library_size": len(EXPERIMENTS),
            },
        )
        write_json(
            breakfix_root / case_id / "trajectory.json",
            {
                "agent": "breakfix-assumption-planner",
                "instructions": "Infer hidden assumptions from the selected diff, rank their risk, select targeted experiments, execute them, and report only observed results.",
                "context": {"diff": diff, "visible_tests": visible_dict},
                "tool_calls": ["read_selected_diff", "infer_assumptions", "rank_assumptions", "select_targeted_experiments"],
                "ground_truth_supplied_to_agent": False,
            },
        )

        fixed_records = []
        for experiment in EXPERIMENTS:
            execution = run_experiment(
                after_dir(root, case_id),
                experiment.id,
                payload_for(experiment),
            )
            evaluation = _evaluation(case_id, experiment.id, execution.as_dict(), ground_truth)
            _record_execution(root, fixed_root, case_id, experiment.id, execution, evaluation)
            fixed_records.append({**execution.as_dict(), "evaluation": evaluation})

        breakfix_records = []
        for experiment_id in selected:
            experiment = experiment_by_id(experiment_id)
            execution = run_experiment(
                after_dir(root, case_id),
                experiment.id,
                payload_for(experiment),
            )
            evaluation = _evaluation(case_id, experiment.id, execution.as_dict(), ground_truth)
            _record_execution(root, breakfix_root, case_id, experiment.id, execution, evaluation)
            breakfix_records.append({**execution.as_dict(), "evaluation": evaluation})

        baseline_flagged = bool(baseline_result["findings"])
        has_fault = bool(ground_truth[case_id].get("fault"))
        baseline_detection = baseline_flagged and has_fault
        baseline_false_approval = has_fault and not baseline_flagged
        baseline_false_positive = (not has_fault) and baseline_flagged
        fixed_detected = any(record["evaluation"]["confirmed_break"] for record in fixed_records)
        breakfix_detected = any(record["evaluation"]["confirmed_break"] for record in breakfix_records)
        case_record = {
            "id": case_id,
            "title": case["title"],
            "surface": case["surface"],
            "visible_tests": visible_dict,
            "baseline": {
                "flagged": baseline_flagged,
                "detection": baseline_detection,
                "false_approval": baseline_false_approval,
                "false_positive": baseline_false_positive,
                "result_path": _relative(root, baseline_case_root / "result.json"),
            },
            "fixed_matrix": {
                "experiments_run": len(fixed_records),
                "detected": fixed_detected,
                "confirmed_experiments": [
                    record["experiment_id"]
                    for record in fixed_records
                    if record["evaluation"]["confirmed_break"]
                ],
                "evidence_path": _relative(root, fixed_root / case_id),
            },
            "breakfix": {
                "assumptions": [assumption.__dict__ for assumption in assumptions],
                "experiments_selected": selected,
                "experiments_run": len(breakfix_records),
                "detected": breakfix_detected,
                "confirmed_experiments": [
                    record["experiment_id"]
                    for record in breakfix_records
                    if record["evaluation"]["confirmed_break"]
                ],
                "evidence_path": _relative(root, breakfix_root / case_id),
            },
        }
        comparison["cases"].append(case_record)

    fault_cases = [case_id for case_id, truth in ground_truth.items() if truth.get("fault")]
    safe_cases = [case_id for case_id, truth in ground_truth.items() if not truth.get("fault")]
    case_records = {record["id"]: record for record in comparison["cases"]}
    comparison["metrics"] = {
        "fault_cases": len(fault_cases),
        "safe_cases": len(safe_cases),
        "baseline": {
            "defect_detection_rate": sum(case_records[case_id]["baseline"]["detection"] for case_id in fault_cases) / len(fault_cases),
            "false_approval_rate": sum(case_records[case_id]["baseline"]["false_approval"] for case_id in fault_cases) / len(fault_cases),
            "false_positive_rate": sum(case_records[case_id]["baseline"]["false_positive"] for case_id in safe_cases) / len(safe_cases),
            "experiments": 0,
        },
        "fixed_matrix": {
            "defect_detection_rate": sum(case_records[case_id]["fixed_matrix"]["detected"] for case_id in fault_cases) / len(fault_cases),
            "experiments": sum(case_records[case_id]["fixed_matrix"]["experiments_run"] for case_id in case_records),
        },
        "breakfix": {
            "defect_detection_rate": sum(case_records[case_id]["breakfix"]["detected"] for case_id in fault_cases) / len(fault_cases),
            "experiments": sum(case_records[case_id]["breakfix"]["experiments_run"] for case_id in case_records),
        },
    }
    comparison["integrity"] = {
        "ground_truth_used_by_evaluator_only": True,
        "real_subprocess_executions": True,
        "live_model_used": False,
        "baseline_is_offline_surrogate": True,
    }
    write_json(evidence_root / "comparison.json", comparison)
    write_text(evidence_root / "stdout.log", json.dumps(comparison, indent=2) + "\n")
    write_text(evidence_root / "stderr.log", "")
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BreakFix Phase 1 comparison.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = run_phase1(args.root)
    print(f"Run: {result['run_id']}")
    for lane in ("baseline", "fixed_matrix", "breakfix"):
        metrics = result["metrics"][lane]
        print(f"{lane}: detection={metrics['defect_detection_rate']:.0%} experiments={metrics['experiments']}")
    print(f"Evidence: evidence/{result['run_id']}")


if __name__ == "__main__":
    main()

