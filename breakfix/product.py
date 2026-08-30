from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_contract import validate_product_planner_response
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "evidence_dir": str(self.evidence_dir),
            "selected_experiments": list(self.selected_experiments),
            "experiments_run": self.experiments_run,
            "provider_status": self.provider_status,
            "regression_valid": self.regression_valid,
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


def _regression_source(payload: dict[str, Any]) -> str:
    encoded = repr(payload)
    return f'''import unittest
import app


class BreakFixRegressionTests(unittest.TestCase):
    def test_observed_change_handles_targeted_perturbation(self):
        payload = {encoded}
        result = app.run(payload)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
'''


def _run_regression_on_broken(project_dir: Path, payload: dict[str, Any], test_command: str) -> dict[str, Any]:
    with isolated_copy(project_dir) as sandbox:
        tests_dir = sandbox / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        generated = tests_dir / "test_breakfix_regression.py"
        generated.write_text(_regression_source(payload), encoding="utf-8")
        execution = run_command(sandbox, test_command, label="generated_regression", timeout_seconds=45)
        return {**execution.as_dict(), "generated_test": str(generated.relative_to(sandbox).as_posix())}


def _assumption_for_experiment(assumptions: list[dict[str, Any]], experiment_id: str) -> dict[str, Any] | None:
    for assumption in assumptions:
        experiment = assumption.get("experiment")
        if isinstance(experiment, dict) and experiment.get("type") == experiment_id:
            return assumption
    return None


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
    assumptions = parsed.get("assumptions") or []
    selected: list[str] = []
    for assumption in assumptions:
        experiment = assumption.get("experiment") if isinstance(assumption, dict) else None
        experiment_id = experiment.get("type") if isinstance(experiment, dict) else None
        if experiment_id in {item.id for item in EXPERIMENTS} and experiment_id not in selected:
            selected.append(experiment_id)
        if len(selected) >= max_experiments:
            break

    write_json(evidence_dir / "planner.json", {
        "change_summary": parsed.get("change_summary"),
        "assumptions": assumptions,
        "unsupported_assumptions": structured.as_dict().get("parsed", {}).get("unsupported_assumptions", []) if isinstance(structured.as_dict().get("parsed"), dict) else [],
        "selected_experiments": selected,
    })
    if not selected:
        summary = {
            **metadata,
            "outcome": "UNSUPPORTED",
            "error_code": "NO_SUPPORTED_ASSUMPTION",
            "selected_experiments": [],
            "experiments_run": 0,
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
    for experiment_id in selected:
        experiment = experiment_by_id(experiment_id)
        payload = payload_for(experiment)
        execution = run_experiment_isolated(execution_root, experiment_id, payload)
        target = evidence_dir / "experiments" / experiment_id
        _write_execution(target, execution)
        record = {
            "experiment_id": experiment_id,
            "description": experiment.description,
            "assumption": _assumption_for_experiment(assumptions, experiment_id),
            "payload": payload,
            "expected_behavior": "the compatible project returns a structured result without a process failure",
            "actual_behavior": {
                "process_failed": execution.process_failed,
                "output": execution.output,
            },
            "evidence_state": "CONFIRMED BREAK" if execution.process_failed else "NO BREAK CONFIRMED",
            "evidence_path": str(target),
        }
        write_json(target / "evidence.json", record)
        records.append(record)
        if execution.process_failed:
            final_outcome = "CONFIRMED BREAK"
            regression = _run_regression_on_broken(execution_root, payload, snapshot.test_command)
            write_json(evidence_dir / "regression" / "broken-run.json", regression)
            regression_valid = bool(regression.get("process_failed"))
            write_text(evidence_dir / "regression" / "test_breakfix_regression.py", _regression_source(payload))
            if not regression_valid:
                final_outcome = "ERROR"
            break

    summary = {
        **metadata,
        "outcome": final_outcome,
        "provider_status": structured.output_contract_status,
        "selected_experiments": selected,
        "experiments_run": len(records),
        "experiment_records": records,
        "regression": {"valid": regression_valid} if regression_valid is not None else None,
        "telemetry_path": str(evidence_dir / "provider-telemetry.json"),
    }
    write_json(evidence_dir / "analysis.json", summary)
    return ProductAnalysis(final_outcome, evidence_dir, tuple(selected), len(records), structured.output_contract_status, regression_valid)


def reproduce(evidence_dir: Path) -> dict[str, Any]:
    """Replay the first selected experiment from a saved confirmed analysis."""
    root = evidence_dir.resolve()
    analysis = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
    records = analysis.get("experiment_records") or []
    confirmed = next((record for record in records if record.get("evidence_state") == "CONFIRMED BREAK"), None)
    if confirmed is None:
        raise RuntimeError("evidence does not contain a confirmed break to reproduce")
    replay_root = Path(analysis.get("project_snapshot") or analysis["project_root"])
    execution = run_experiment_isolated(replay_root, confirmed["experiment_id"], confirmed["payload"])
    target = root / "reproduction" / confirmed["experiment_id"]
    _write_execution(target, execution)
    result = {
        "experiment_id": confirmed["experiment_id"],
        "reproduced": execution.process_failed,
        "evidence_path": str(target),
    }
    write_json(root / "reproduction" / "result.json", result)
    return result
