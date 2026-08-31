import json
import tempfile
import unittest
from pathlib import Path

from breakfix.agent_contract import validate_product_planner_response, validate_fix_response
from breakfix.applicability import assess_probe_applicability
from breakfix.experiments import experiment_by_id
from breakfix.fixes import verify_fix
from breakfix.models import ExecutionResult
from breakfix.product import _evaluate_product_execution, _run_regression_on_broken, analyze_change
from breakfix.git_project import ChangeSnapshot
from breakfix.provider import ProviderAttempt, ProviderResponse, StructuredProviderResult


def _proposal(experiment_id: str, *, target: str = "app.py:run", hypothesis: str = "the assumption holds") -> dict:
    experiment = experiment_by_id(experiment_id)
    return {
        "type": experiment_id,
        "target": target,
        "hypothesis": hypothesis,
        "perturbation": experiment.perturbation,
        "observable": experiment.observable,
        "failure_predicate": experiment.failure_predicate,
        "why_this_probe_tests_this_assumption": "the exact catalogue perturbation exercises the named boundary",
        "parameters": {},
    }


def _assumption(statement: str, surface: str, experiment_id: str, *, failure: str = "the target fails") -> dict:
    return {
        "id": "A1",
        "statement": statement,
        "surface": surface,
        "risk": "high",
        "evidence": [{"file": "app.py", "location": "run", "reason": "change evidence"}],
        "failure_if_false": failure,
        "experiment": _proposal(experiment_id),
    }


class CorrectnessHardeningTests(unittest.TestCase):
    def test_timing_retry_hypothesis_rejects_unrelated_concurrency_probe(self):
        result = assess_probe_applicability(
            _assumption("requests are idempotent under retries", "timing", "concurrent_duplicate", failure="a retry duplicates the request"),
            _proposal("concurrent_duplicate"),
            experiment_by_id("concurrent_duplicate"),
        )
        self.assertFalse(result["applicable"])
        self.assertEqual(result["status"], "NOT EXECUTABLE")

    def test_browser_dom_hypothesis_rejects_generic_state_probe(self):
        result = assess_probe_applicability(
            _assumption("the browser DOM download anchor is created", "state", "state_legacy", failure="the browser download is missing"),
            _proposal("state_legacy"),
            experiment_by_id("state_legacy"),
        )
        self.assertFalse(result["applicable"])
        self.assertEqual(result["status"], "UNSUPPORTED")

    def test_browser_world_hypothesis_rejects_event_probe_without_browser_observable(self):
        result = assess_probe_applicability(
            _assumption("the browser world exposes the correct download event", "world", "events_reordered", failure="the browser event is not observed"),
            _proposal("events_reordered"),
            experiment_by_id("events_reordered"),
        )
        self.assertFalse(result["applicable"])
        self.assertEqual(result["status"], "NOT EXECUTABLE")

    def test_process_crash_from_missing_module_is_harness_failure_not_break(self):
        execution = ExecutionResult("input_empty", ["python", "-c", ""], 1, False, "", "ModuleNotFoundError: No module named app")
        self.assertTrue(execution.harness_failed)
        self.assertFalse(execution.target_failed)
        result = _evaluate_product_execution(execution, {"applicable": True})
        self.assertEqual(result["evidence_state"], "HARNESS FAILURE")

    def test_dependency_setup_failure_is_not_target_evidence(self):
        execution = ExecutionResult("input_empty", ["python", "-c", ""], 1, False, "", "ERROR: Could not install dependency; pip install failed")
        self.assertEqual(execution.failure_kind, "HARNESS_FAILURE")
        self.assertFalse(_evaluate_product_execution(execution, {"applicable": True})["failure_predicate_matched"])

    def test_missing_concrete_observable_cannot_confirm_break(self):
        execution = ExecutionResult("input_empty", ["python", "-c", ""], 1, False, "", "")
        self.assertFalse(execution.concrete_observable)
        result = _evaluate_product_execution(execution, {"applicable": True})
        self.assertNotEqual(result["evidence_state"], "CONFIRMED BREAK")
        self.assertFalse(result["evidence_sufficient"])

    def test_applicable_probe_with_matching_target_failure_is_confirmed(self):
        execution = ExecutionResult("input_empty", ["python", "-c", ""], 1, False, "Traceback\nZeroDivisionError: division by zero", "", output_captured=False)
        result = _evaluate_product_execution(
            execution,
            assess_probe_applicability(_assumption("the collection is non-empty", "input", "input_empty"), _proposal("input_empty"), experiment_by_id("input_empty")),
        )
        self.assertEqual(result["evidence_state"], "CONFIRMED BREAK")
        self.assertEqual(result["failure_classification"], "EXPECTED PREDICATE FAILURE")
        self.assertTrue(result["failure_predicate_matched"])

    def test_budget_selection_marks_only_selected_and_executed_assumptions(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "app.py").write_text("def run(payload): return {'ok': True}\n", encoding="utf-8")
            (project / "tests").mkdir()
            first = _assumption("the collection is non-empty", "input", "input_empty")
            second = _assumption("the value has a numeric boundary", "input", "input_boundary_zero")
            third = _assumption("the request is idempotent under retries", "timing", "retry_duplicate")
            second["id"] = "A2"
            third["id"] = "A3"
            provider = _PlannerProvider([first, second, third])
            snapshot = ChangeSnapshot(project, "test", None, "diff", ("app.py",), "test", "python -m unittest discover -s tests -v")
            evidence = project / "evidence"
            analyze_change(snapshot, evidence, provider=provider, max_experiments=1)
            planner = json.loads((evidence / "planner.json").read_text(encoding="utf-8"))
            statuses = {item["id"]: (item.get("selection_status"), item.get("execution_status")) for item in planner["assumptions"]}
            self.assertEqual(statuses["A1"], ("SELECTED", "EXECUTED"))
            self.assertEqual([item["execution_status"] for item in planner["assumptions"]].count("EXECUTED"), 1)

    def test_generated_regression_is_the_artifact_not_a_generic_project_test_command(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "app.py").write_text("def run(payload): return 1 / len(payload['items'])\n", encoding="utf-8")
            contract = {"failure_predicate": "the target raises when the input collection is empty"}
            result = _run_regression_on_broken(project, {"items": []}, contract)
            self.assertTrue(result["valid"])
            self.assertEqual(result["test_file"], "tests/test_breakfix_regression.py")
            self.assertIn("test_breakfix_regression.py", result["command_used"])
            self.assertNotIn("npm", " ".join(result["command_used"]))
            self.assertEqual(result["result_against_broken"], "FAIL")

    def test_failed_verification_is_not_verified_and_exposes_failed_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "analysis.json").write_text(json.dumps({
                "project_root": str(root),
                "project_snapshot": str(root / "approved_snapshot"),
                "test_command": "python -m unittest discover -s tests -v",
                "experiment_records": [{
                    "experiment_id": "input_empty",
                    "payload": {"items": []},
                    "evidence_state": "CONFIRMED BREAK",
                    "evidence_sufficient": True,
                    "failure_predicate_matched": True,
                }],
            }), encoding="utf-8")
            approved = root / "approved_snapshot"
            (approved / "tests").mkdir(parents=True)
            (approved / "app.py").write_text("def run(payload): return 1 / len(payload['items'])\n", encoding="utf-8")
            (approved / "tests" / "test_breakfix_regression.py").write_text("", encoding="utf-8")
            regression = root / "regression"
            regression.mkdir()
            (regression / "test_breakfix_regression.py").write_text(
                "import unittest\nimport app\nclass T(unittest.TestCase):\n def test_confirmed_failure_does_not_recur(self):\n  self.fail('confirmed target failure reproduced')\n",
                encoding="utf-8",
            )
            result = verify_fix(root)
            self.assertEqual(result["status"], "NOT VERIFIED")
            self.assertTrue(result["candidate_fix_rejected_by_verification"])
            self.assertTrue(result["failed_checks"])
            self.assertIn("The proposed fix did not satisfy BreakFix's verification checks.", result["user_message"])

    def test_product_planner_semantic_contract_rejects_mismatched_perturbation(self):
        assumption = _assumption("the collection is non-empty", "input", "input_empty")
        assumption["experiment"]["perturbation"] = {"items": [1]}
        result = validate_product_planner_response(json.dumps({"change_summary": "change", "assumptions": [assumption]}))
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_experiment_ids"], [])
        self.assertEqual(result["assumptions"][0]["execution_status"], "NOT EXECUTABLE")

    def test_fix_contract_requires_evidence_reference_and_causal_explanation(self):
        result = validate_fix_response(json.dumps({"summary": "x", "patch": "diff", "files_changed": [], "tests_to_run": []}))
        self.assertFalse(result["valid"])
        self.assertIn("evidence_reference", " ".join(result["validation_failures"]))
        self.assertIn("causal_explanation", " ".join(result["validation_failures"]))


class _PlannerProvider:
    provider = "test"
    model = "test"
    reasoning_effort = "high"

    def __init__(self, assumptions):
        self.assumptions = assumptions

    def complete_structured(self, _prompt, *, validator, max_recovery_attempts):
        parsed = {"change_summary": "bounded test", "assumptions": self.assumptions}
        response = ProviderResponse(
            response_text=json.dumps(parsed), reasoning_text="", provider=self.provider, model=self.model,
            input_tokens=1, output_tokens=1, total_tokens=2, latency_ms=1, monetary_cost_usd=0,
            finish_reason="stop", response_format="json_object",
        )
        return StructuredProviderResult(True, parsed, response, None, (ProviderAttempt(1, response, None, None),))


if __name__ == "__main__":
    unittest.main()
