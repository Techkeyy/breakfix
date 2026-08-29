import json
import unittest
from pathlib import Path

from breakfix.agent_contract import validate_phase2b_baseline_response, validate_phase2b_breakfix_response
from breakfix.phase2b import PHASE2B_CASE_IDS, PHASE2B_MAX_EXPERIMENTS, _evaluate_execution, _select_experiments, _targeted_outcome


ROOT = Path(__file__).resolve().parents[1]


class Phase2BContractTests(unittest.TestCase):
    def test_holdout_is_fresh_balanced_and_numeric(self):
        truth = json.loads((ROOT / "benchmark" / "phase2b_ground_truth.json").read_text(encoding="utf-8"))
        self.assertEqual(PHASE2B_CASE_IDS, tuple(f"h{i:02d}" for i in range(15, 31)))
        self.assertEqual(sum(bool(truth[case_id]["fault"]) for case_id in PHASE2B_CASE_IDS), 8)
        self.assertEqual(sum(not truth[case_id]["fault"] for case_id in PHASE2B_CASE_IDS), 8)
        for case_id in PHASE2B_CASE_IDS:
            public = json.loads((ROOT / "benchmark" / "phase2b_holdout" / case_id / "public.json").read_text(encoding="utf-8"))
            self.assertEqual(public["id"], case_id)

    def test_execution_states_require_oracle_and_payload_evidence(self):
        truth = {"fault": True, "fault_experiments": ["retry_duplicate"], "expected_outputs": {"retry_duplicate": {"accepted": 1}}}
        failure = {"command": ["python", "-c"], "exit_code": 1, "timed_out": False, "stdout": "", "stderr": "KeyError", "process_failed": True, "output": None, "payload": {}}
        clear = {"command": ["python", "-c"], "exit_code": 0, "timed_out": False, "stdout": "{}", "stderr": "", "process_failed": False, "output": {"accepted": 1}, "payload": {}}
        self.assertEqual(_evaluate_execution(truth, "retry_duplicate", failure)["evidence_state"], "CONFIRMED_BREAK")
        self.assertEqual(_evaluate_execution(truth, "retry_duplicate", clear)["evidence_state"], "CLEARED")
        self.assertEqual(_evaluate_execution(truth, "world_dst", clear)["evidence_state"], "UNSUPPORTED")

    def test_budget_deduplicates_and_caps_ranked_proposals(self):
        response = {
            "valid": True,
            "assumptions": [
                {"proposed_experiment": {"id": "retry_duplicate"}},
                {"proposed_experiment": {"id": "retry_duplicate"}},
                {"proposed_experiment": {"id": "input_empty"}},
                {"proposed_experiment": {"id": "world_dst"}},
            ],
            "unsupported_assumptions": [],
        }
        selected, _ = _select_experiments(response)
        self.assertEqual(PHASE2B_MAX_EXPERIMENTS, 3)
        self.assertEqual(selected, ["retry_duplicate", "input_empty", "world_dst"])

    def test_cleared_supported_probe_can_report_no_break_with_unsupported_assumption(self):
        validation = {"valid": True}
        record = {"evaluation": {"evidence_state": "CLEARED"}}
        self.assertEqual(_targeted_outcome(validation, [record]), "NO BREAK CONFIRMED")

    def test_phase2b_model_contracts(self):
        baseline = validate_phase2b_baseline_response(json.dumps({
            "change_summary": "The visible change preserves the ordinary path.",
            "recommendation": "NO_BREAK_FOUND",
            "findings": [],
            "tests_run": [],
            "tool_actions": [],
            "retries": 0,
            "final_conclusion": "No break was found in the supplied context.",
        }))
        breakfix = validate_phase2b_breakfix_response(json.dumps({
            "change_summary": "The handler assumes a current record shape.",
            "assumptions": [{
                "id": "record-shape",
                "statement": "Older records contain the accessed field.",
                "surface": "state",
                "evidence": ["after/app.py:3"],
                "failure_if_false": "The handler raises when the field is absent.",
                "risk": "high",
                "proposed_experiment": {"id": "state_legacy", "parameters": {}, "rationale": "Exercise the prior record shape."},
            }],
            "tests_run": [],
            "tool_actions": [],
            "retries": 0,
            "final_conclusion": "The runtime must test the assumption.",
        }))
        self.assertTrue(baseline["valid"])
        self.assertEqual(baseline["recommendation"], "NO_BREAK_FOUND")
        self.assertTrue(breakfix["valid"])
        self.assertEqual(breakfix["assumptions"][0]["proposed_experiment"]["id"], "state_legacy")


if __name__ == "__main__":
    unittest.main()
