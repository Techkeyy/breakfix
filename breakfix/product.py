from __future__ import annotations

import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_contract import validate_product_planner_response
from .applicability import assess_probe_applicability
from .evidence import write_json, write_text
from .executor import (
    copy_sanitized_project,
    isolated_copy,
    run_command,
    run_experiment_isolated,
)
from .experiments import BASE_CONTEXT, EXPERIMENTS, experiment_by_id, payload_for
from .git_project import ChangeSnapshot
from .product_prompts import PRODUCT_PROMPT_ID, render_product_planner_prompt
from .provider import DirectProvider, StructuredProviderResult


PRODUCT_MAX_EXPERIMENTS = 3


@dataclass(frozen=True)
class ProductAnalysis:
    outcome: str
    evidence_dir: Path
    selected_experiments: tuple[str, ...]
    experiments_run: int
    provider_status: str
    regression_valid: bool | None
    error_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "evidence_dir": str(self.evidence_dir),
            "selected_experiments": list(self.selected_experiments),
            "experiments_run": self.experiments_run,
            "provider_status": self.provider_status,
            "regression_valid": self.regression_valid,
            "error_code": self.error_code,
        }


def _write_execution(target: Path, execution: Any) -> None:
    write_json(target / "result.json", execution.as_dict())
    write_text(target / "stdout.log", execution.stdout)
    write_text(target / "stderr.log", execution.stderr)


def _provider_telemetry(result: StructuredProviderResult) -> dict[str, Any]:
    responses = [attempt.response for attempt in result.attempts if attempt.response is not None]

    def total(field: str) -> int | float | None:
        values = [getattr(response, field) for response in responses]
        return sum(values) if values and all(value is not None for value in values) else None

    return {
        "model_calls": len(result.attempts),
        "successful_provider_responses": len(responses),
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "total_tokens": total("total_tokens"),
        "monetary_cost_usd": total("monetary_cost_usd"),
        "latency_ms": total("latency_ms"),
        "retries": sum(response.retries for response in responses),
        "finish_reasons": [response.finish_reason for response in responses],
        "reasoning_content_present": any(bool(response.reasoning_text) for response in responses),
        "response_formats": sorted({response.response_format for response in responses if response.response_format}),
    }


def _regression_source(payload: dict[str, Any], contract: dict[str, Any]) -> str:
    encoded = repr(payload)
    predicate = repr(contract.get("failure_predicate", "the confirmed target failure must not recur"))
    return f'''import unittest
import app


class BreakFixRegressionTests(unittest.TestCase):
    def test_confirmed_failure_does_not_recur(self):
        """The exact confirmed perturbation must no longer raise ({predicate})."""
        payload = {encoded}
        try:
            app.run(payload)
        except Exception as exc:
            self.fail(f"confirmed target failure reproduced: {{type(exc).__name__}}: {{exc}}")


if __name__ == "__main__":
    unittest.main()
'''


def _regression_command(test_file: str = "test_breakfix_regression.py") -> list[str]:
    return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", test_file, "-v"]


def _run_regression_on_broken(project_dir: Path, payload: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    with isolated_copy(project_dir) as sandbox:
        tests_dir = sandbox / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        generated = tests_dir / "test_breakfix_regression.py"
        generated.write_text(_regression_source(payload, contract), encoding="utf-8")
        command = _regression_command(generated.name)
        execution = run_command(sandbox, command, label="generated_regression", timeout_seconds=45)
        transcript = f"{execution.stdout}\n{execution.stderr}".upper()
        valid = bool(
            execution.exit_code not in (None, 0)
            and not execution.timed_out
            and not execution.harness_failed
            and ("FAIL" in transcript or "ERROR" in transcript)
        )
        return {
            **execution.as_dict(),
            "valid": valid,
            "generated_test": str(generated.relative_to(sandbox).as_posix()),
            "test_file": str(generated.relative_to(sandbox).as_posix()),
            "test_assertion": "app.run(exact_confirmed_payload) must not raise the confirmed target failure",
            "command_used": command,
            "result_against_broken": "FAIL" if valid else "INVALID",
            "failure_predicate": contract.get("failure_predicate"),
        }


def _assumption_for_experiment(assumptions: list[dict[str, Any]], experiment_id: str) -> dict[str, Any] | None:
    for assumption in assumptions:
        experiment = assumption.get("experiment")
        if isinstance(experiment, dict) and experiment.get("type") == experiment_id:
            return assumption
    return None


def _experiment_contract(assumption: dict[str, Any], experiment: Any) -> dict[str, Any]:
    proposal = assumption.get("experiment") if isinstance(assumption.get("experiment"), dict) else {}
    return {
        "assumption_id": assumption.get("id"),
        "target": proposal.get("target"),
        "hypothesis": proposal.get("hypothesis"),
        "perturbation": proposal.get("perturbation"),
        "observable": proposal.get("observable") or experiment.observable,
        "failure_predicate": proposal.get("failure_predicate") or experiment.failure_predicate,
        "why_this_probe_tests_this_assumption": proposal.get("why_this_probe_tests_this_assumption"),
        "oracle": "deterministic runtime failure predicate",
        "catalogue_target": experiment.target,
        "capability": experiment.capability,
    }


def _evaluate_product_execution(execution: Any, applicability: dict[str, Any]) -> dict[str, Any]:
    if not applicability.get("applicable"):
        return {
            "evidence_state": applicability.get("status", "NOT EXECUTABLE"),
            "evidence_sufficient": False,
            "failure_predicate_matched": False,
            "observable": None,
            "reason": applicability.get("reason", "probe is not executable"),
        }
    if execution.harness_failed:
        return {
            "evidence_state": "HARNESS FAILURE",
            "evidence_sufficient": False,
            "failure_predicate_matched": False,
            "observable": "execution harness failure; target behavior was not established",
            "reason": "the subprocess did not produce trustworthy target evidence",
        }
    if execution.target_failed and execution.concrete_observable:
        return {
            "evidence_state": "CONFIRMED BREAK",
            "evidence_sufficient": True,
            "failure_predicate_matched": True,
            "observable": f"target process exited {execution.exit_code} with a captured target failure",
            "reason": "applicable probe created its target condition and the captured observable matched the runtime failure predicate",
        }
    if execution.target_failed:
        return {
            "evidence_state": "INCONCLUSIVE",
            "evidence_sufficient": False,
            "failure_predicate_matched": False,
            "observable": None,
            "reason": "target failure had no concrete observable sufficient to distinguish or replay it",
        }
    if execution.output_captured:
        return {
            "evidence_state": "NO BREAK CONFIRMED",
            "evidence_sufficient": True,
            "failure_predicate_matched": False,
            "observable": "structured target output captured",
            "reason": "applicable probe completed and returned a structured observable without the predicted failure",
        }
    return {
        "evidence_state": "INCONCLUSIVE",
        "evidence_sufficient": False,
        "failure_predicate_matched": False,
        "observable": None,
        "reason": "no concrete observable was captured",
    }


def analyze_change(
    snapshot: ChangeSnapshot,
    evidence_dir: Path,
    *,
    provider: DirectProvider | None = None,
    max_experiments: int = PRODUCT_MAX_EXPERIMENTS,
    max_recovery_attempts: int = 1,
) -> ProductAnalysis:
    """Run the reusable BreakFix loop for one selected compatible change."""
    if max_experiments < 1:
        raise ValueError("max_experiments must be positive")
    evidence_dir = evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    provider = provider or DirectProvider()

    execution_root = copy_sanitized_project(snapshot.project_root, evidence_dir / "project_snapshot")

    with isolated_copy(execution_root) as sandbox:
        visible = run_command(sandbox, snapshot.test_command, label="visible_tests", timeout_seconds=45)
    write_json(evidence_dir / "visible-tests" / "result.json", visible.as_dict())
    write_text(evidence_dir / "visible-tests" / "stdout.log", visible.stdout)
    write_text(evidence_dir / "visible-tests" / "stderr.log", visible.stderr)

    prompt = render_product_planner_prompt(
        snapshot.project_root,
        snapshot.diff,
        snapshot.task,
        visible.stdout + visible.stderr,
    )
    write_text(evidence_dir / "planner-prompt.txt", prompt)
    structured = provider.complete_structured(
        prompt,
        validator=validate_product_planner_response,
        max_recovery_attempts=max_recovery_attempts,
    )
    write_json(evidence_dir / "provider-recovery.json", structured.as_dict())
    write_json(evidence_dir / "provider-telemetry.json", _provider_telemetry(structured))

    metadata = {
        "project_root": str(snapshot.project_root),
        "project_snapshot": str(execution_root),
        "change_kind": snapshot.change_kind,
        "reference": snapshot.reference,
        "changed_files": list(snapshot.changed_files),
        "task": snapshot.task,
        "test_command": snapshot.test_command,
        "prompt_id": PRODUCT_PROMPT_ID,
        "max_experiments": max_experiments,
        "max_recovery_attempts": max_recovery_attempts,
        "ground_truth_supplied_to_agent": False,
        "dependency_installation": "disabled by default",
        "change_resolution": {
            "requested_kind": snapshot.change_kind,
            "requested_reference": snapshot.reference,
            "resolved_base": snapshot.resolved_base,
            "resolved_head": snapshot.resolved_head,
            "resolved_reference": snapshot.resolved_reference,
        },
    }
    write_json(evidence_dir / "change.json", {
        "change_kind": snapshot.change_kind,
        "reference": snapshot.reference,
        "task": snapshot.task,
        "changed_files": list(snapshot.changed_files),
        "change_resolution": metadata["change_resolution"],
        "diff": snapshot.diff,
        "visible_test_command": snapshot.test_command,
    })
    write_json(evidence_dir / "analysis-metadata.json", metadata)

    if not structured.success:
        summary = {
            **metadata,
            "outcome": "ERROR",
            "error_code": structured.failure_code,
            "error_detail": structured.attempts[-1].output_failure if structured.attempts else None,
            "selected_experiments": [],
            "experiments_run": 0,
            "regression": None,
        }
        write_json(evidence_dir / "analysis.json", summary)
        return ProductAnalysis("ERROR", evidence_dir, (), 0, structured.output_contract_status, None)

    parsed = structured.parsed or {}
    normalized_validation = validate_product_planner_response(json.dumps(parsed))
    if normalized_validation.get("valid") and isinstance(normalized_validation.get("parsed"), dict):
        parsed = normalized_validation["parsed"]
    assumptions = parsed.get("assumptions") or []
    unsupported = list(parsed.get("unsupported_assumptions") or normalized_validation.get("unsupported_assumptions", []))
    selected: list[str] = []
    for assumption in assumptions:
        if not isinstance(assumption, dict) or assumption.get("execution_status") != "CANDIDATE":
            continue
        experiment = assumption.get("experiment") if isinstance(assumption, dict) else None
        experiment_id = experiment.get("type") if isinstance(experiment, dict) else None
        if experiment_id in {item.id for item in EXPERIMENTS} and experiment_id not in selected:
            selected.append(experiment_id)
        if len(selected) >= max_experiments:
            break

    for assumption in assumptions:
        if not isinstance(assumption, dict):
            continue
        experiment = assumption.get("experiment")
        experiment_id = experiment.get("type") if isinstance(experiment, dict) else None
        if assumption.get("execution_status") == "CANDIDATE":
            assumption["selection_status"] = "SELECTED" if experiment_id in selected else "CANDIDATE"
            assumption["selected_for_execution"] = experiment_id in selected

    write_json(evidence_dir / "planner.json", {
        "change_summary": parsed.get("change_summary"),
        "assumptions": assumptions,
        "unsupported_assumptions": unsupported,
        "selected_experiments": selected,
    })
    if not selected:
        summary = {
            **metadata,
            "outcome": "UNSUPPORTED",
            "error_code": "NO_SUPPORTED_ASSUMPTION",
            "selected_experiments": [],
            "experiments_run": 0,
            "assumptions": assumptions,
            "unsupported_assumptions": unsupported,
            "regression": None,
        }
        write_json(evidence_dir / "analysis.json", summary)
        return ProductAnalysis("UNSUPPORTED", evidence_dir, (), 0, structured.output_contract_status, None)

    control_payload = deepcopy(BASE_CONTEXT)
    with isolated_copy(execution_root) as sandbox:
        from .executor import run_experiment

        control = run_experiment(sandbox, "control", control_payload, timeout_seconds=15)
    _write_execution(evidence_dir / "control", control)

    records: list[dict[str, Any]] = []
    regression_valid: bool | None = None
    final_outcome = "NO BREAK CONFIRMED"
    error_code: str | None = None
    for experiment_id in selected:
        experiment = experiment_by_id(experiment_id)
        assumption = _assumption_for_experiment(assumptions, experiment_id) or {}
        proposal = assumption.get("experiment") if isinstance(assumption.get("experiment"), dict) else {}
        applicability = assumption.get("applicability") if isinstance(assumption.get("applicability"), dict) else assess_probe_applicability(assumption, proposal, experiment)
        contract = _experiment_contract(assumption, experiment)
        payload = payload_for(experiment)
        execution = run_experiment_isolated(execution_root, experiment_id, payload)
        target = evidence_dir / "experiments" / experiment_id
        _write_execution(target, execution)
        evaluation = _evaluate_product_execution(execution, applicability)
        actual_behavior = {
            "process_failed": execution.process_failed,
            "failure_kind": execution.failure_kind,
            "target_failed": execution.target_failed,
            "harness_failed": execution.harness_failed,
            "exit_code": execution.exit_code,
            "timed_out": execution.timed_out,
            "output_captured": execution.output_captured,
            "concrete_observable": execution.concrete_observable,
            "observable": evaluation.get("observable"),
            "output": execution.output,
        }
        record = {
            "experiment_id": experiment_id,
            "description": experiment.description,
            "assumption_id": assumption.get("id"),
            "assumption": assumption,
            "contract": contract,
            "payload": payload,
            "expected_behavior": f"Observe {contract.get('observable')}; predicted failure: {contract.get('failure_predicate')}",
            "failure_predicate": contract.get("failure_predicate"),
            "actual_behavior": actual_behavior,
            "evidence_state": evaluation["evidence_state"],
            "evidence_sufficient": evaluation["evidence_sufficient"],
            "failure_predicate_matched": evaluation["failure_predicate_matched"],
            "evidence_reason": evaluation["reason"],
            "execution_status": "EXECUTED",
            "evidence_path": str(target),
        }
        assumption["execution_status"] = "EXECUTED"
        assumption["executed"] = True
        if evaluation["evidence_state"] == "CONFIRMED BREAK":
            regression = _run_regression_on_broken(execution_root, payload, contract)
            write_json(evidence_dir / "regression" / "broken-run.json", regression)
            write_text(evidence_dir / "regression" / "test_breakfix_regression.py", _regression_source(payload, contract))
            regression_valid = bool(regression.get("valid"))
            record["regression"] = {
                "valid": regression_valid,
                "test_file": regression.get("test_file"),
                "test_assertion": regression.get("test_assertion"),
                "command_used": regression.get("command_used"),
                "result_against_broken": regression.get("result_against_broken"),
            }
            if not regression_valid:
                record["evidence_state"] = "REGRESSION INVALID"
                record["evidence_sufficient"] = False
                error_code = "REGRESSION_INVALID" if not regression.get("harness_failed") else "REGRESSION_HARNESS_FAILURE"
                final_outcome = "ERROR" if regression.get("harness_failed") else "UNSUPPORTED"
            else:
                final_outcome = "CONFIRMED BREAK"
            write_json(target / "evidence.json", record)
            records.append(record)
            break
        write_json(target / "evidence.json", record)
        records.append(record)
        if evaluation["evidence_state"] == "HARNESS FAILURE":
            final_outcome = "ERROR"
            error_code = "HARNESS_FAILURE"
            break
        if evaluation["evidence_state"] == "INCONCLUSIVE":
            final_outcome = "UNSUPPORTED"
            error_code = "INSUFFICIENT_OBSERVABLE"
            break

    summary = {
        **metadata,
        "outcome": final_outcome,
        "provider_status": structured.output_contract_status,
        "selected_experiments": selected,
        "experiments_run": len(records),
        "experiment_records": records,
        "regression": {"valid": regression_valid} if regression_valid is not None else None,
        "assumptions": assumptions,
        "unsupported_assumptions": unsupported,
        "executed_experiments": [record["experiment_id"] for record in records if record.get("execution_status") == "EXECUTED"],
        "error_code": error_code,
        "semantic_applicability_gate": True,
        "telemetry_path": str(evidence_dir / "provider-telemetry.json"),
    }
    write_json(evidence_dir / "planner.json", {
        "change_summary": parsed.get("change_summary"),
        "assumptions": assumptions,
        "unsupported_assumptions": unsupported,
        "selected_experiments": selected,
    })
    write_json(evidence_dir / "analysis.json", summary)
    return ProductAnalysis(final_outcome, evidence_dir, tuple(selected), len(records), structured.output_contract_status, regression_valid, error_code)


def reproduce(evidence_dir: Path) -> dict[str, Any]:
    """Replay the first selected experiment from a saved confirmed analysis."""
    root = evidence_dir.resolve()
    analysis = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
    records = analysis.get("experiment_records") or []
    confirmed = next((record for record in records if record.get("evidence_state") == "CONFIRMED BREAK"), None)
    if confirmed is None:
        raise RuntimeError("evidence does not contain a confirmed break to reproduce")
    if not confirmed.get("evidence_sufficient") or not confirmed.get("failure_predicate_matched"):
        raise RuntimeError("confirmed evidence does not satisfy the hardened replay contract")
    replay_root = Path(analysis.get("project_snapshot") or analysis["project_root"])
    execution = run_experiment_isolated(replay_root, confirmed["experiment_id"], confirmed["payload"])
    target = root / "reproduction" / confirmed["experiment_id"]
    _write_execution(target, execution)
    result = {
        "experiment_id": confirmed["experiment_id"],
        "reproduced": execution.target_failed and execution.concrete_observable,
        "failure_kind": execution.failure_kind,
        "concrete_observable": execution.concrete_observable,
        "evidence_path": str(target),
    }
    write_json(root / "reproduction" / "result.json", result)
    return result
