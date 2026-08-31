"""Offline forensic replay for a preserved post-hardening evaluation.

This tool intentionally has no provider client and never makes a network call.
It reads the saved Attempt 2 recovery records, validates the preserved model
responses with the current deterministic contract, and executes only selected
catalogue probes against the preserved after-snapshots. The original raw
evidence is read-only; all output is written to a new directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from breakfix.agent_contract import validate_product_planner_response  # noqa: E402
from breakfix.applicability import assess_probe_applicability  # noqa: E402
from breakfix.executor import run_experiment_isolated  # noqa: E402
from breakfix.experiments import EXPERIMENTS, experiment_by_id, payload_for  # noqa: E402
from breakfix.product import (  # noqa: E402
    _evaluate_product_execution,
    _experiment_contract,
    _run_regression_on_broken,
)


TABLE_FIELDS = (
    "case_id",
    "truth",
    "provider_status",
    "planner_valid",
    "assumption_count",
    "proposed_count",
    "applicability",
    "selected_count",
    "probe_build",
    "execution_attempted_result",
    "evidence_gate",
    "final_verdict",
    "error_code",
    "error_message",
    "root_stage",
)


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _last_response(recovery: dict[str, Any]) -> dict[str, Any] | None:
    for attempt in reversed(recovery.get("attempts") or []):
        response = attempt.get("response")
        if isinstance(response, dict) and isinstance(response.get("response_text"), str):
            return response
    return None


def _error_messages(recovery: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for attempt in recovery.get("attempts") or []:
        for field in ("output_failure", "provider_error"):
            message = attempt.get(field)
            if isinstance(message, str) and message:
                messages.append(message)
    return messages


def _frozen_error_message(recovery: dict[str, Any], analysis: dict[str, Any]) -> str | None:
    detail = analysis.get("error_detail")
    if isinstance(detail, str) and detail:
        return detail
    messages = _error_messages(recovery)
    return messages[-1] if messages else None


def _frozen_provider_status(recovery: dict[str, Any], analysis: dict[str, Any]) -> str:
    value = recovery.get("output_contract_status") or analysis.get("provider_status") or recovery.get("failure_code")
    return str(value or "UNKNOWN")


def _planner_data(case_root: Path) -> dict[str, Any]:
    planner = _read_json(case_root / "planner.json", {})
    return planner if isinstance(planner, dict) else {}


def _assumptions(planner: dict[str, Any]) -> list[dict[str, Any]]:
    values = planner.get("assumptions")
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def _applicability_text(assumptions: list[dict[str, Any]]) -> str:
    values: list[str] = []
    for assumption in assumptions:
        applicability = assumption.get("applicability")
        if not isinstance(applicability, dict):
            continue
        status = applicability.get("status", "UNKNOWN")
        reason = applicability.get("reason", "")
        values.append(f"{assumption.get('id', '?')}={status}: {reason}".strip())
    return " | ".join(values) if values else "none recorded"


def _execution_text(analysis: dict[str, Any]) -> str:
    records = analysis.get("experiment_records")
    if not isinstance(records, list) or not records:
        return "not attempted"
    values: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        actual = record.get("actual_behavior") or {}
        kind = actual.get("failure_kind", "unknown") if isinstance(actual, dict) else "unknown"
        values.append(f"{record.get('experiment_id', '?')}: {kind}")
    return "; ".join(values) if values else "not attempted"


def _evidence_text(analysis: dict[str, Any]) -> str:
    records = analysis.get("experiment_records")
    if not isinstance(records, list) or not records:
        return "none"
    values: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        state = record.get("evidence_state", "unknown")
        sufficient = record.get("evidence_sufficient")
        matched = record.get("failure_predicate_matched")
        values.append(f"{record.get('experiment_id', '?')}: {state} (sufficient={sufficient}, predicate={matched})")
    return "; ".join(values) if values else "none"


def _root_stage(provider_status: str, outcome: str | None, error_message: str | None) -> str:
    if provider_status == "PROVIDER_OUTPUT_ERROR":
        return "provider contract / parsing"
    if provider_status == "PROVIDER_ERROR":
        if error_message and "budget exhausted" in error_message:
            return "provider budget enforcement"
        return "provider transport"
    if outcome == "UNSUPPORTED":
        return "applicability / selection"
    if outcome == "ERROR":
        return "provider / execution error"
    if outcome:
        return "execution / evidence"
    return "not reached"


def _frozen_row(case_id: str, oracle_case: dict[str, Any], raw_case_root: Path) -> dict[str, Any]:
    recovery = _read_json(raw_case_root / "provider-recovery.json", {})
    analysis = _read_json(raw_case_root / "analysis.json", {})
    planner = _planner_data(raw_case_root)
    assumptions = _assumptions(planner)
    selected = planner.get("selected_experiments")
    selected = selected if isinstance(selected, list) else analysis.get("selected_experiments") or []
    provider_status = _frozen_provider_status(recovery, analysis)
    outcome = analysis.get("outcome") if isinstance(analysis, dict) else None
    error_message = _frozen_error_message(recovery, analysis) if provider_status != "OK" or outcome == "ERROR" else None
    records = analysis.get("experiment_records") if isinstance(analysis, dict) else None
    executed_count = len(records) if isinstance(records, list) else int(analysis.get("experiments_run") or 0)
    execution = _execution_text(analysis)
    evidence = _evidence_text(analysis)
    return {
        "case_id": case_id,
        "truth": "FAULTY" if oracle_case.get("faulty") else "SAFE",
        "provider_status": provider_status,
        "planner_valid": bool(recovery.get("success")),
        "assumption_count": len(assumptions),
        "proposed_count": sum(1 for item in assumptions if isinstance(item.get("experiment"), dict)),
        "applicability": _applicability_text(assumptions),
        "selected_count": len(selected),
        "probe_build": "SUCCESS" if selected and executed_count else "NOT REACHED",
        "execution_attempted_result": execution,
        "evidence_gate": evidence,
        "final_verdict": outcome or "not reached",
        "error_code": analysis.get("error_code") or recovery.get("failure_code"),
        "error_message": error_message or "none",
        "root_stage": _root_stage(provider_status, outcome, error_message),
    }


def _response_shapes(recovery: dict[str, Any]) -> Counter[str]:
    shapes: Counter[str] = Counter()
    for attempt in recovery.get("attempts") or []:
        response = attempt.get("response")
        if not isinstance(response, dict):
            continue
        try:
            parsed = json.loads(response.get("response_text", ""))
        except (TypeError, json.JSONDecodeError):
            continue
        for assumption in parsed.get("assumptions", []) if isinstance(parsed, dict) else []:
            if not isinstance(assumption, dict):
                continue
            if "experiment" not in assumption:
                shapes["experiment field omitted"] += 1
            elif assumption.get("experiment") is None:
                shapes["experiment:null"] += 1
            elif isinstance(assumption.get("experiment"), dict):
                shapes["experiment object"] += 1
            else:
                shapes["experiment non-object"] += 1
    return shapes


def _error_taxonomy(case_records: dict[str, dict[str, Any]], raw_case_roots: dict[str, Path]) -> list[dict[str, Any]]:
    categories: list[dict[str, Any]] = []
    output_cases = [case_id for case_id, record in case_records.items() if record["provider_status"] == "PROVIDER_OUTPUT_ERROR"]
    transport_cases: list[str] = []
    budget_cases: list[str] = []
    output_messages: Counter[str] = Counter()
    transport_messages: Counter[str] = Counter()
    budget_messages: Counter[str] = Counter()
    shape_counts: Counter[str] = Counter()
    for case_id, raw_case_root in raw_case_roots.items():
        recovery = _read_json(raw_case_root / "provider-recovery.json", {})
        messages = _error_messages(recovery)
        for message in messages:
            if case_id in output_cases and "schema validation failed" in message:
                output_messages[message] += 1
            elif "budget exhausted" in message:
                budget_messages[message] += 1
            elif "direct provider transport error" in message:
                transport_messages[message] += 1
        if any("direct provider transport error" in message for message in messages):
            transport_cases.append(case_id)
        if any("budget exhausted" in message for message in messages):
            budget_cases.append(case_id)
        if case_id in output_cases:
            shape_counts.update(_response_shapes(recovery))

    categories.append({
        "category": "PROVIDER_OUTPUT_ERROR / planner schema mismatch",
        "count": len(output_cases),
        "case_ids": sorted(output_cases),
        "exact_failure_text_counts": dict(output_messages),
        "file_function": "breakfix/agent_contract.py::validate_product_planner_response",
        "stage": "provider contract / parsing",
        "input_shape": "well-formed planner assumptions with experiment:null or an omitted experiment field; observed shapes: " + ", ".join(f"{key}={value}" for key, value in sorted(shape_counts.items())),
        "hardening_introduced": True,
        "should_be_unsupported": True,
        "diagnosis": "The prompt allowed an assumption with no executable catalogue probe, but the validator treated that representation as malformed provider output.",
    })
    categories.append({
        "category": "PROVIDER_ERROR / direct transport DNS",
        "count": len(transport_cases),
        "case_ids": sorted(transport_cases),
        "exact_failure_text_counts": dict(transport_messages),
        "file_function": "breakfix/provider.py::DirectProvider.complete",
        "stage": "provider transport",
        "input_shape": "no model response was received; planner input shape is therefore unavailable",
        "hardening_introduced": False,
        "should_be_unsupported": False,
        "diagnosis": "The direct adapter exhausted its transport retries with name-resolution failure before a planner output existed.",
    })
    categories.append({
        "category": "PROVIDER_ERROR / frozen completion ceiling",
        "count": len(budget_cases),
        "case_ids": sorted(budget_cases),
        "exact_failure_text_counts": dict(budget_messages),
        "file_function": "scripts/run_post_hardening_evaluation.py::BudgetedProvider.complete_structured / complete",
        "stage": "provider budget enforcement",
        "input_shape": "no model response was received after the global frozen completion ceiling; planner input shape is unavailable",
        "hardening_introduced": False,
        "should_be_unsupported": False,
        "diagnosis": "The evaluator refused another completion after the sealed global ceiling was reached; this is not evidence that the case was unsupported.",
    })
    return categories


def _replay_case(case_id: str, oracle_case: dict[str, Any], raw_root: Path) -> dict[str, Any]:
    raw_case_root = raw_root / "breakfix" / case_id
    recovery = _read_json(raw_case_root / "provider-recovery.json", {})
    response = _last_response(recovery)
    base = {
        "case_id": case_id,
        "truth": "FAULTY" if oracle_case.get("faulty") else "SAFE",
        "provider_calls": 0,
        "preserved_model_response": response is not None,
    }
    if response is None:
        return {**base, "replay_status": "NO_PRESERVED_MODEL_RESPONSE", "planner_valid_after_repair": None, "selected_experiments": [], "experiments": []}

    # The preserved final run predates the structured predicate field. This
    # compatibility mode adds only catalogue-declared defaults while keeping
    # the current live planner contract strict.
    validation = validate_product_planner_response(
        response["response_text"], allow_legacy_structured_predicate=True
    )
    if not validation.get("valid"):
        return {
            **base,
            "replay_status": "PROVIDER_OUTPUT_ERROR",
            "planner_valid_after_repair": False,
            "validation_failures": validation.get("validation_failures", []),
            "selected_experiments": [],
            "experiments": [],
        }

    assumptions = validation.get("assumptions") or []
    selected = validation.get("selected_experiment_ids") or []
    after_root = raw_root / "workspace" / "benchmark" / "post_hardening_holdout" / case_id / "after"
    experiment_records: list[dict[str, Any]] = []
    for experiment_id in selected:
        experiment = experiment_by_id(experiment_id)
        assumption = next(
            (
                item
                for item in assumptions
                if isinstance(item.get("experiment"), dict) and item["experiment"].get("type") == experiment_id
            ),
            {},
        )
        applicability = assumption.get("applicability") if isinstance(assumption, dict) else None
        if not isinstance(applicability, dict):
            applicability = assess_probe_applicability(assumption, assumption.get("experiment", {}), experiment)
        execution = run_experiment_isolated(after_root, experiment_id, payload_for(experiment))
        contract = _experiment_contract(assumption, experiment)
        evaluation = _evaluate_product_execution(
            execution, applicability, experiment, contract.get("structured_failure_predicate")
        )
        record = {
            "experiment_id": experiment_id,
            "failure_kind": execution.failure_kind,
            "output": execution.output,
            "exit_code": execution.exit_code,
            "duration_ms": execution.duration_ms,
            "evidence_state": evaluation.get("evidence_state"),
            "evidence_sufficient": evaluation.get("evidence_sufficient"),
            "failure_predicate_matched": evaluation.get("failure_predicate_matched"),
            "reason": evaluation.get("reason"),
        }
        if evaluation.get("evidence_state") == "CONFIRMED BREAK":
            regression = _run_regression_on_broken(after_root, payload_for(experiment), contract)
            record["regression"] = regression
            if not regression.get("valid"):
                record["evidence_state"] = "REGRESSION INVALID"
                record["evidence_sufficient"] = False
                record["failure_predicate_matched"] = False
                record["reason"] = "confirmed runtime observation did not produce a valid broken-project regression"
        experiment_records.append(record)

    states = [record.get("evidence_state") for record in experiment_records]
    if "CONFIRMED BREAK" in states and all(
        record.get("evidence_state") != "CONFIRMED BREAK" or record.get("regression", {}).get("valid")
        for record in experiment_records
    ):
        replay_status = "CONFIRMED BREAK"
    elif "REGRESSION INVALID" in states:
        replay_status = "ERROR" if any(
            record.get("regression", {}).get("harness_failed") for record in experiment_records
        ) else "UNSUPPORTED"
    elif "HARNESS FAILURE" in states:
        replay_status = "ERROR"
    elif any(state in {"INCONCLUSIVE", "NOT EXECUTABLE"} for state in states):
        replay_status = "UNSUPPORTED"
    elif selected:
        replay_status = "NO BREAK CONFIRMED"
    else:
        replay_status = "UNSUPPORTED"
    return {
        **base,
        "replay_status": replay_status,
        "planner_valid_after_repair": True,
        "assumption_count": len(assumptions),
        "proposed_count": sum(1 for item in assumptions if isinstance(item.get("experiment"), dict)),
        "applicability": _applicability_text(assumptions),
        "selected_experiments": selected,
        "experiments": experiment_records,
    }


def _replay_metrics(replays: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item.get("replay_status") for item in replays)
    executed = [item for item in replays if item.get("experiments")]
    confirmed_faults = sum(1 for item in replays if item.get("truth") == "FAULTY" and item.get("replay_status") == "CONFIRMED BREAK")
    false_confirmed = sum(1 for item in replays if item.get("truth") == "SAFE" and item.get("replay_status") == "CONFIRMED BREAK")
    return {
        "label": "DEVELOPMENT REPLAY / NOT FINAL EVALUATION",
        "case_count": len(replays),
        "preserved_model_responses": sum(1 for item in replays if item.get("preserved_model_response")),
        "cases_with_no_preserved_model_response": counts.get("NO_PRESERVED_MODEL_RESPONSE", 0),
        "planner_valid_after_repair": sum(1 for item in replays if item.get("planner_valid_after_repair") is True),
        "planner_output_errors_after_repair": counts.get("PROVIDER_OUTPUT_ERROR", 0),
        "planned_experiments": sum(len(item.get("selected_experiments") or []) for item in replays),
        "observed_experiments": sum(len(item.get("experiments") or []) for item in replays),
        "executed_case_count": len(executed),
        "confirmed_fault_cases": confirmed_faults,
        "false_confirmed_breaks": false_confirmed,
        "replay_status_counts": dict(sorted(counts.items(), key=lambda item: str(item[0]))),
        "provider_calls": 0,
    }


def run(raw_root: Path, oracle_path: Path, output_root: Path) -> None:
    if output_root.exists():
        raise SystemExit(f"Refusing to overwrite existing forensic output: {output_root}")
    oracle = _read_json(oracle_path)
    cases = oracle.get("cases") if isinstance(oracle, dict) else None
    if not isinstance(cases, dict) or len(cases) != 16:
        raise SystemExit("Expected an external oracle with exactly 16 cases")
    raw_breakfix = raw_root / "breakfix"
    if not raw_breakfix.is_dir():
        raise SystemExit(f"Missing preserved Attempt 2 breakfix evidence: {raw_breakfix}")

    raw_case_roots = {case_id: raw_breakfix / case_id for case_id in sorted(cases)}
    frozen_rows = {case_id: _frozen_row(case_id, cases[case_id], raw_case_roots[case_id]) for case_id in sorted(cases)}
    replays = [_replay_case(case_id, cases[case_id], raw_root) for case_id in sorted(cases)]
    replay_by_case = {item["case_id"]: item for item in replays}

    output_root.mkdir(parents=True)
    _write_json(output_root / "forensic-table.json", list(frozen_rows.values()))
    with (output_root / "forensic-table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_FIELDS)
        writer.writeheader()
        writer.writerows(frozen_rows.values())
    _write_json(output_root / "error-taxonomy.json", _error_taxonomy(frozen_rows, raw_case_roots))
    _write_json(output_root / "offline-replay.json", replays)
    _write_json(output_root / "offline-replay-metrics.json", _replay_metrics(replays))
    _write_json(output_root / "manifest.json", {
        "mode": "offline forensic replay",
        "raw_attempt2_root": str(raw_root),
        "external_oracle_path": str(oracle_path),
        "cases": sorted(cases),
        "provider_calls": 0,
        "frozen_evidence_modified": False,
        "replay_status_by_case": {case_id: replay_by_case[case_id]["replay_status"] for case_id in sorted(replay_by_case)},
    })

    print(json.dumps({
        "output_root": str(output_root),
        "cases": len(cases),
        "provider_calls": 0,
        "frozen_evidence_modified": False,
        "replay_metrics": _replay_metrics(replays),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--oracle-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.raw_root.resolve(), args.oracle_path.resolve(), args.output_root.resolve())


if __name__ == "__main__":
    main()
