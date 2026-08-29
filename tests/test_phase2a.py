import json
import unittest
from pathlib import Path

from breakfix.agent_contract import validate_phase2a_baseline_response, validate_phase2a_breakfix_response
from breakfix.phase2a import PHASE2A_CASE_IDS, _evaluate_execution


ROOT = Path(__file__).resolve().parents[1]


class Phase2AContractTests(unittest.TestCase):
    def test_holdout_is_balanced_and_numeric(self):
        truth = json.loads((ROOT / "benchmark" / "phase2a_ground_truth.json").read_text(encoding="utf-8"))
        self.assertEqual(len(PHASE2A_CASE_IDS), 14)
        self.assertEqual(sum(bool(truth[case_id]["fault"]) for case_id in PHASE2A_CASE_IDS), 7)
        self.assertEqual(sum(not truth[case_id]["fault"] for case_id in PHASE2A_CASE_IDS), 7)
        for case_id in PHASE2A_CASE_IDS:
            public = json.loads((ROOT / "benchmark" / "phase2a_holdout" / case_id / "public.json").read_text(encoding="utf-8"))
            self.assertEqual(public["id"], case_id)

    def test_execution_states_require_oracle_and_evidence(self):
        truth = {"fault": True, "fault_experiments": ["retry_duplicate"], "expected_outputs": {"retry_duplicate": {"total_charged": 25}}}
        failure = {"command": ["python", "-c"], "exit_code": 1, "timed_out": False, "stdout": "", "stderr": "ValueError", "process_failed": True, "output": None}
        clear = {"command": ["python", "-c"], "exit_code": 0, "timed_out": False, "stdout": "{}", "stderr": "", "process_failed": False, "output": {"total_charged": 25}}
        self.assertEqual(_evaluate_execution(truth, "retry_duplicate", failure)["evidence_state"], "CONFIRMED_BREAK")
        self.assertEqual(_evaluate_execution(truth, "retry_duplicate", clear)["evidence_state"], "CLEARED")
        self.assertEqual(_evaluate_execution(truth, "world_dst", clear)["evidence_state"], "UNSUPPORTED")

    def test_phase2a_model_contracts_preserve_uncertainty(self):
        baseline = validate_phase2a_baseline_response(json.dumps({
            "change_summary": "No verified issue.",
            "verdict": "INCONCLUSIVE",
            "findings": [],
            "tests_run": [],
            "tool_actions": [],
            "retries": 0,
            "final_conclusion": "The visible tests pass, but the hidden boundary is unverified.",
        }))
        breakfix = validate_phase2a_breakfix_response(json.dumps({
            "change_summary": "The handler assumes a current record shape.",
            "assumptions": [{
                "id": "record-shape",
                "statement": "Older records contain the accessed field.",
                "surface": "state",
                "evidence": ["after/app.py:2"],
                "failure_if_false": "The handler raises when the field is absent.",
                "risk": "high",
                "proposed_experiment": {"id": "state_legacy", "parameters": {}, "rationale": "Exercise the prior record shape."},
            }],
            "tests_run": [],
            "tool_actions": [],
            "retries": 0,
            "final_conclusion": "Run the deterministic experiment before deciding.",
        }))
        self.assertTrue(baseline["valid"])
        self.assertEqual(baseline["verdict"], "INCONCLUSIVE")
        self.assertTrue(breakfix["valid"])
        self.assertEqual(breakfix["selected_experiment_ids"], ["state_legacy"])


if __name__ == "__main__":
    unittest.main()
