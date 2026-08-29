from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "final-independent-evaluation-v1"
PRODUCT_CHECKPOINT = "13b8c89"
EXPECTED_CASE_COUNT = 16
EXPECTED_MATRIX_EXPERIMENTS = 8
PRODUCT_MAX_EXPERIMENTS = 3


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_git_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={PROJECT_ROOT}", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _aggregate_telemetry(items: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = (
        "model_calls",
        "successful_provider_responses",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "monetary_cost_usd",
        "latency_ms",
        "retries",
    )
    result: dict[str, Any] = {key: 0 for key in numeric}
    result["finish_reasons"] = []
    result["response_formats"] = []
    result["reasoning_content_present"] = False
    for item in items:
        for key in numeric:
            value = item.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                result[key] += value
        result["finish_reasons"].extend(item.get("finish_reasons") or [])
        result["response_formats"].extend(item.get("response_formats") or [])
        result["reasoning_content_present"] = result["reasoning_content_present"] or bool(
            item.get("reasoning_content_present")
        )
    result["response_formats"] = sorted(set(result["response_formats"]))
    return result


def _copy_history_free_workspace(target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=False)
    shutil.copytree(PROJECT_ROOT / "breakfix", target / "breakfix")
    shutil.copytree(PROJECT_ROOT / "benchmark" / "final_holdout", target / "benchmark" / "final_holdout")
    for name in ("pyproject.toml", ".env.example"):
        source = PROJECT_ROOT / name
        if source.exists():
            shutil.copy2(source, target / name)
    if (target / ".git").exists():
        raise RuntimeError("history-free workspace unexpectedly contains .git")
    return target


def _public_case_files(case_root: Path) -> list[Path]:
    return sorted(path for path in case_root.rglob("*") if path.is_file())


def _leakage_audit(public_root: Path, truth: dict[str, dict[str, Any]]) -> dict[str, Any]:
    case_dirs = sorted(path for path in public_root.iterdir() if path.is_dir())
    forbidden_public_terms = (
        "expected_outputs",
        "oracle",
        "fault_experiments",
        "seeded_fault",
        "safe_case",
        "unsafe_case",
    )
    term_hits: list[str] = []
    truth_paths_in_public: list[str] = []
    for case_root in case_dirs:
        for path in _public_case_files(case_root):
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            for term in forbidden_public_terms:
                if term in lower:
                    term_hits.append(f"{path.relative_to(public_root)}:{term}")
            if "truth" in lower and path.name != "public.json":
                truth_paths_in_public.append(str(path.relative_to(public_root)))
    truth_case_ids = set(truth)
    public_case_ids = {path.name for path in case_dirs}
    return {
        "public_case_count": len(case_dirs),
        "truth_case_count": len(truth_case_ids),
        "case_id_sets_match": public_case_ids == truth_case_ids,
        "forbidden_term_hits": term_hits,
        "truth_path_hits": truth_paths_in_public,
        "passed": (
            len(case_dirs) == EXPECTED_CASE_COUNT
            and public_case_ids == truth_case_ids
            and not term_hits
            and not truth_paths_in_public
        ),
    }


def _public_case_prompt_snapshot(case_root: Path, prompt: str) -> dict[str, Any]:
    public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
    return {
        "case_id": public["id"],
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_id": "final-generic-comparator-v1",
        "ground_truth_supplied_to_agent": False,
    }


def _execution_complete(result: dict[str, Any]) -> bool:
    required = (
        "command",
        "stdout",
        "stderr",
        "exit_code",
        "timed_out",
        "duration_ms",
        "process_failed",
    )
    return all(key in result for key in required)


def _oracle_outcome(
    execution: dict[str, Any],
    expected_outputs: dict[str, Any],
    experiment_id: str,
) -> dict[str, Any]:
    if experiment_id not in expected_outputs:
        return {
            "state": "UNSUPPORTED",
            "evidence_complete": _execution_complete(execution),
            "matches_expected": None,
            "oracle_available": False,
        }
    complete = _execution_complete(execution)
    if not complete:
        return {
            "state": "ERROR",
            "evidence_complete": False,
            "matches_expected": None,
            "oracle_available": True,
        }
    matches = (
        not bool(execution.get("process_failed"))
        and execution.get("output") == expected_outputs[experiment_id]
    )
    return {
        "state": "NO BREAK CONFIRMED" if matches else "CONFIRMED BREAK",
        "evidence_complete": True,
        "matches_expected": matches,
        "oracle_available": True,
    }


def _diff_for_case(case_root: Path) -> str:
    before = (case_root / "before" / "app.py").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines(True)
    after = (case_root / "after" / "app.py").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines(True)
    return "".join(
        difflib.unified_diff(before, after, fromfile="a/app.py", tofile="b/app.py")
    )


def _copy_public_product_evidence(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("evaluation.json"))


def _baseline_telemetry(result: Any, case_id: str) -> dict[str, Any]:
    responses = [attempt.response for attempt in result.attempts if attempt.response]
    return {
        "case_id": case_id,
        "model_calls": len(result.attempts),
        "successful_provider_responses": len(responses),
        "input_tokens": sum((response.input_tokens or 0) for response in responses),
        "output_tokens": sum((response.output_tokens or 0) for response in responses),
        "total_tokens": sum((response.total_tokens or 0) for response in responses),
        "monetary_cost_usd": sum((response.monetary_cost_usd or 0) for response in responses),
        "latency_ms": sum(response.latency_ms for response in responses),
        "retries": sum(response.retries for response in responses),
        "finish_reasons": [response.finish_reason for response in responses],
        "response_formats": [
            response.response_format
            for response in responses
            if response.response_format
        ],
        "reasoning_content_present": any(
            bool(response.reasoning_text) for response in responses
        ),
    }


def _score_case_lane(
    case_results: list[dict[str, Any]],
    truth: dict[str, dict[str, Any]],
    *,
    lane: str,
) -> dict[str, Any]:
    confirmed_faults = 0
    false_confirmed_breaks = 0
    errors = 0
    unsupported = 0
    for result in case_results:
        case_truth = truth[result["case_id"]]
        state = result.get("state")
        if state == "ERROR":
            errors += 1
        if state == "UNSUPPORTED":
            unsupported += 1
        if state == "CONFIRMED BREAK":
            if case_truth["fault"]:
                confirmed_faults += 1
            else:
                false_confirmed_breaks += 1
    fault_count = sum(1 for item in truth.values() if item["fault"])
    safe_count = len(truth) - fault_count
    recall = confirmed_faults / fault_count if fault_count else None
    false_rate = false_confirmed_breaks / safe_count if safe_count else None
    eligible = confirmed_faults == fault_count and false_confirmed_breaks == 0 and errors == 0
    return {
        "lane": lane,
        "fault_cases": fault_count,
        "safe_cases": safe_count,
        "confirmed_fault_cases": confirmed_faults,
        "seeded_fault_recall": recall,
        "false_confirmed_breaks": false_confirmed_breaks,
        "false_confirmed_break_rate": false_rate,
        "error_cases": errors,
        "unsupported_cases": unsupported,
        "eligible": eligible,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen final independent evaluation."
    )
    parser.add_argument("--truth-path", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument(
        "--public-evidence-root",
        type=Path,
        default=PROJECT_ROOT / "evidence",
    )
    args = parser.parse_args()

    truth_path = args.truth_path.resolve()
    if not truth_path.is_file():
        raise SystemExit(f"truth file not found: {truth_path}")
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    if not isinstance(truth, dict):
        raise SystemExit("truth file must contain an object")

    run_id = "final-eval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_root = (
        args.raw_root.resolve()
        if args.raw_root
        else (Path(tempfile.gettempdir()) / f"breakfix-{run_id}").resolve()
    )
    if raw_root.exists():
        raise SystemExit(f"refusing to overwrite raw root: {raw_root}")
    raw_root.mkdir(parents=True)
    workspace = _copy_history_free_workspace(raw_root / "workspace")
    public_root = workspace / "benchmark" / "final_holdout"
    public_evidence = args.public_evidence_root.resolve() / run_id
    public_evidence.mkdir(parents=True, exist_ok=False)
    if str(truth_path).startswith(str(workspace)) or str(truth_path).startswith(
        str(public_evidence)
    ):
        raise SystemExit("truth file must remain outside evaluation and published evidence roots")

    leakage = _leakage_audit(public_root, truth)
    _write_json(raw_root / "leakage-audit.json", leakage)
    if not leakage["passed"]:
        raise SystemExit("final holdout leakage audit failed")

    sys.path.insert(0, str(workspace))
    from breakfix.agent_contract import validate_phase2b_baseline_response
    from breakfix.experiments import EXPERIMENTS, payload_for
    from breakfix.final_eval_prompts import (
        FINAL_GENERIC_PROMPT_ID,
        render_final_generic_prompt,
    )
    from breakfix.git_project import ChangeSnapshot
    from breakfix.product import analyze_change
    from breakfix.provider import DirectProvider
    from breakfix.executor import run_experiment_isolated

    case_dirs = sorted(path for path in public_root.iterdir() if path.is_dir())
    if len(case_dirs) != EXPECTED_CASE_COUNT:
        raise SystemExit(f"expected {EXPECTED_CASE_COUNT} holdout cases, found {len(case_dirs)}")

    provider = DirectProvider()
    if (
        provider.provider != "deepseek"
        or provider.model != "deepseek-v4-pro"
        or provider.reasoning_effort != "high"
        or provider.max_output_tokens != 12000
    ):
        raise SystemExit("provider configuration does not match frozen final protocol")
    credential_present = bool(
        os.environ.get("BREAKFIX_DEEPSEEK_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
    )
    if not credential_present:
        raise SystemExit("required DeepSeek credential is not present")

    public_baseline_root = public_evidence / "trajectories" / "baseline"
    public_breakfix_root = public_evidence / "trajectories" / "breakfix"
    public_fixed_root = public_evidence / "fixed-matrix"
    raw_baseline_root = raw_root / "baseline"
    raw_breakfix_root = raw_root / "breakfix"
    raw_fixed_root = raw_root / "fixed-matrix"
    baseline_results: list[dict[str, Any]] = []
    baseline_telemetry: list[dict[str, Any]] = []
    breakfix_results: list[dict[str, Any]] = []
    breakfix_telemetry: list[dict[str, Any]] = []
    fixed_results: list[dict[str, Any]] = []
    breakfix_experiment_total = 0
    breakfix_regressions_valid = 0
    started_all = time.perf_counter()

    for case_root in case_dirs:
        case_id = case_root.name
        public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
        expected_outputs = truth[case_id]["expected_outputs"]

        prompt = render_final_generic_prompt(case_root)
        prompt_snapshot = {
            "case_id": case_id,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "prompt_id": FINAL_GENERIC_PROMPT_ID,
            "ground_truth_supplied_to_agent": False,
        }
        started = time.perf_counter()
        baseline = provider.complete_structured(
            prompt,
            validator=validate_phase2b_baseline_response,
            max_recovery_attempts=1,
        )
        baseline_duration_ms = round((time.perf_counter() - started) * 1000)
        baseline_data = baseline.as_dict()
        parsed = baseline.parsed or {}
        recommendation = parsed.get("recommendation") if baseline.success else None
        expected_recommendation = (
            "POTENTIAL_BREAK" if truth[case_id]["fault"] else "NO_BREAK_FOUND"
        )
        baseline_result = {
            "case_id": case_id,
            "recommendation": recommendation,
            "provider_status": baseline.output_contract_status,
            "valid_contract": baseline.success,
            "correct_against_external_truth": bool(
                baseline.success and recommendation == expected_recommendation
            ),
            "expected_recommendation_internal": expected_recommendation,
            "duration_ms": baseline_duration_ms,
        }
        baseline_results.append(baseline_result)
        baseline_telemetry.append(_baseline_telemetry(baseline, case_id))
        _write_json(
            raw_baseline_root / case_id / "replay.json",
            {
                "case_id": case_id,
                "prompt": prompt,
                "prompt_sha256": prompt_snapshot["prompt_sha256"],
                "prompt_id": FINAL_GENERIC_PROMPT_ID,
                "provider_result": baseline_data,
                "result": baseline_result,
            },
        )
        _write_json(
            public_baseline_root / case_id / "replay.json",
            {
                "case_id": case_id,
                "prompt_sha256": prompt_snapshot["prompt_sha256"],
                "prompt_id": FINAL_GENERIC_PROMPT_ID,
                "ground_truth_supplied_to_agent": False,
                "provider_result": baseline_data,
                "result": {
                    key: value
                    for key, value in baseline_result.items()
                    if key != "expected_recommendation_internal"
                },
            },
        )

        snapshot = ChangeSnapshot(
            project_root=(case_root / "after").resolve(),
            change_kind="final-holdout",
            reference=case_id,
            diff=_diff_for_case(case_root),
            changed_files=("app.py",),
            task=public["task"],
            test_command=public["test_command"],
        )
        breakfix_evidence = raw_breakfix_root / case_id
        started = time.perf_counter()
        product_analysis = analyze_change(
            snapshot,
            breakfix_evidence,
            provider=provider,
            max_experiments=PRODUCT_MAX_EXPERIMENTS,
            max_recovery_attempts=1,
        )
        breakfix_duration_ms = round((time.perf_counter() - started) * 1000)
        breakfix_experiment_total += product_analysis.experiments_run
        if product_analysis.regression_valid:
            breakfix_regressions_valid += 1
        analysis = json.loads((breakfix_evidence / "analysis.json").read_text(encoding="utf-8"))
        provider_telemetry = json.loads(
            (breakfix_evidence / "provider-telemetry.json").read_text(encoding="utf-8")
        )
        breakfix_telemetry.append({"case_id": case_id, **provider_telemetry})
        records: list[dict[str, Any]] = []
        saw_confirmed = False
        saw_error = product_analysis.provider_status in {
            "PROVIDER_ERROR",
            "PROVIDER_OUTPUT_ERROR",
        }
        saw_unsupported = False
        for record in analysis.get("experiment_records") or []:
            experiment_id = record["experiment_id"]
            result_path = breakfix_evidence / "experiments" / experiment_id / "result.json"
            execution = (
                json.loads(result_path.read_text(encoding="utf-8"))
                if result_path.is_file()
                else {}
            )
            oracle = _oracle_outcome(execution, expected_outputs, experiment_id)
            if oracle["state"] == "CONFIRMED BREAK":
                saw_confirmed = True
            elif oracle["state"] == "ERROR":
                saw_error = True
            elif oracle["state"] == "UNSUPPORTED":
                saw_unsupported = True
            records.append(
                {
                    "experiment_id": experiment_id,
                    "state": oracle["state"],
                    "evidence_complete": oracle["evidence_complete"],
                    "process_failed": execution.get("process_failed"),
                    "duration_ms": execution.get("duration_ms"),
                }
            )
        if saw_error or product_analysis.outcome == "ERROR":
            case_state = "ERROR"
        elif saw_confirmed:
            case_state = "CONFIRMED BREAK"
        elif not records or saw_unsupported or product_analysis.outcome == "UNSUPPORTED":
            case_state = "UNSUPPORTED"
        else:
            case_state = "NO BREAK CONFIRMED"
        breakfix_result = {
            "case_id": case_id,
            "state": case_state,
            "provider_status": product_analysis.provider_status,
            "selected_experiments": list(product_analysis.selected_experiments),
            "experiments_run": product_analysis.experiments_run,
            "regression_valid": product_analysis.regression_valid,
            "records": records,
            "duration_ms": breakfix_duration_ms,
        }
        breakfix_results.append(breakfix_result)
        _write_json(
            raw_breakfix_root / case_id / "evaluation.json",
            {**breakfix_result, "truth": truth[case_id]},
        )
        _copy_public_product_evidence(
            breakfix_evidence, public_breakfix_root / case_id
        )
        _write_json(public_breakfix_root / case_id / "evaluation-summary.json", breakfix_result)

    fixed_started = time.perf_counter()
    for case_root in case_dirs:
        case_id = case_root.name
        expected_outputs = truth[case_id]["expected_outputs"]
        case_result = {
            "case_id": case_id,
            "experiments": [],
            "confirmed_break": False,
            "errors": 0,
            "unsupported": 0,
        }
        for experiment in EXPERIMENTS:
            execution = run_experiment_isolated(
                case_root / "after",
                experiment.id,
                payload_for(experiment),
            )
            execution_data = execution.as_dict()
            oracle = _oracle_outcome(execution_data, expected_outputs, experiment.id)
            item = {
                "case_id": case_id,
                "experiment_id": experiment.id,
                "state": oracle["state"],
                "evidence_complete": oracle["evidence_complete"],
                "process_failed": execution_data.get("process_failed"),
                "duration_ms": execution_data.get("duration_ms"),
            }
            case_result["experiments"].append(item)
            if oracle["state"] == "CONFIRMED BREAK":
                case_result["confirmed_break"] = True
            if oracle["state"] == "ERROR":
                case_result["errors"] += 1
            if oracle["state"] == "UNSUPPORTED":
                case_result["unsupported"] += 1
            target = public_fixed_root / case_id / experiment.id
            _write_json(target / "result.json", execution_data)
            _write_text(target / "stdout.log", execution.stdout)
            _write_text(target / "stderr.log", execution.stderr)
            _write_json(
                raw_fixed_root / case_id / experiment.id / "evaluation.json",
                {
                    **item,
                    "truth": truth[case_id],
                    "expected_output": expected_outputs.get(experiment.id),
                    "actual_output": execution_data.get("output"),
                },
            )
        fixed_results.append(case_result)
    fixed_duration_ms = round((time.perf_counter() - fixed_started) * 1000)

    baseline_lane_results = [
        {
            **result,
            "state": (
                "CONFIRMED BREAK"
                if result["recommendation"] == "POTENTIAL_BREAK"
                else (
                    "NO BREAK CONFIRMED"
                    if result["recommendation"] == "NO_BREAK_FOUND"
                    else "ERROR"
                )
            ),
        }
        for result in baseline_results
    ]
    baseline_score = _score_case_lane(
        baseline_lane_results, truth, lane="generic-baseline"
    )
    fixed_case_states = [
        {
            "case_id": item["case_id"],
            "state": (
                "CONFIRMED BREAK"
                if item["confirmed_break"]
                else ("ERROR" if item["errors"] else "NO BREAK CONFIRMED")
            ),
        }
        for item in fixed_results
    ]
    fixed_score = _score_case_lane(
        fixed_case_states, truth, lane="fixed-matrix"
    )
    fixed_score.update(
        {
            "planned_experiments": len(case_dirs) * EXPECTED_MATRIX_EXPERIMENTS,
            "observed_experiments": len(fixed_results) * EXPECTED_MATRIX_EXPERIMENTS,
            "unsupported_probe_count": sum(
                item["unsupported"] for item in fixed_results
            ),
            "execution_error_count": sum(item["errors"] for item in fixed_results),
            "duration_ms": fixed_duration_ms,
        }
    )
    breakfix_score = _score_case_lane(
        breakfix_results, truth, lane="breakfix-targeted"
    )
    breakfix_score.update(
        {
            "planned_experiments": len(case_dirs) * PRODUCT_MAX_EXPERIMENTS,
            "observed_experiments": breakfix_experiment_total,
            "max_experiments_per_case": PRODUCT_MAX_EXPERIMENTS,
            "regression_valid_count": breakfix_regressions_valid,
            "duration_ms": round((time.perf_counter() - started_all) * 1000),
        }
    )
    if fixed_score["eligible"] and breakfix_score["eligible"]:
        reduction = (
            (fixed_score["observed_experiments"] - breakfix_score["observed_experiments"])
            / fixed_score["observed_experiments"]
            * 100
        )
        per_defect = (
            breakfix_score["observed_experiments"]
            / breakfix_score["confirmed_fault_cases"]
            if breakfix_score["confirmed_fault_cases"]
            else None
        )
    else:
        reduction = None
        per_defect = None
    total_telemetry = _aggregate_telemetry(baseline_telemetry + breakfix_telemetry)
    gate = (
        "PASS"
        if fixed_score["eligible"]
        and breakfix_score["eligible"]
        and breakfix_score["observed_experiments"]
        < fixed_score["observed_experiments"]
        else "FAIL"
    )
    summary = {
        "run_id": run_id,
        "protocol_id": PROTOCOL_ID,
        "protocol_status": "frozen before evaluation",
        "product_checkpoint": PRODUCT_CHECKPOINT,
        "git_head_at_start": _safe_git_head(),
        "history_free_workspace": str(workspace),
        "public_holdout_root": str(public_root),
        "private_truth_path": str(truth_path),
        "deepseek_credential_present": credential_present,
        "started_at_utc": _utc_now(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "holdout_case_count": len(case_dirs),
        "holdout_manifest_sha256": _sha256(public_root / "manifest.json"),
        "leakage_audit": leakage,
        "baseline": baseline_score,
        "fixed_matrix": fixed_score,
        "breakfix": breakfix_score,
        "experiment_reduction_percentage": reduction,
        "experiments_per_confirmed_defect": per_defect,
        "primary_gate": gate,
        "telemetry": {
            "baseline": _aggregate_telemetry(baseline_telemetry),
            "breakfix": _aggregate_telemetry(breakfix_telemetry),
            "all_live_provider_calls": total_telemetry,
        },
        "live_case_results": {
            "baseline": baseline_results,
            "breakfix": breakfix_results,
        },
        "fixed_case_results": fixed_results,
    }
    _write_json(raw_root / "final-summary.json", summary)
    public_summary = json.loads(json.dumps(summary))
    public_summary.pop("private_truth_path", None)
    public_summary.pop("history_free_workspace", None)
    for item in public_summary["live_case_results"]["baseline"]:
        item.pop("expected_recommendation_internal", None)
    public_summary["fixed_case_results"] = [
        {
            "case_id": item["case_id"],
            "experiments": item["experiments"],
            "confirmed_break": item["confirmed_break"],
        }
        for item in fixed_results
    ]
    _write_json(public_evidence / "final-summary.json", public_summary)
    _write_json(public_evidence / "leakage-audit.json", leakage)
    _write_json(
        public_evidence / "run-metadata.json",
        {
            "run_id": run_id,
            "protocol_id": PROTOCOL_ID,
            "product_checkpoint": PRODUCT_CHECKPOINT,
            "holdout_manifest_sha256": summary["holdout_manifest_sha256"],
            "public_holdout_cases": len(case_dirs),
            "truth_loaded_externally": True,
            "truth_path_published": False,
            "git_head_at_start": summary["git_head_at_start"],
            "deepseek_credential_present": credential_present,
        },
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "primary_gate": gate,
                "baseline": baseline_score,
                "fixed_matrix": fixed_score,
                "breakfix": breakfix_score,
                "experiment_reduction_percentage": reduction,
                "public_evidence": str(public_evidence),
                "raw_evidence": str(raw_root),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
