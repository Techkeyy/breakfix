import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from breakfix.agent_contract import validate_phase2b_baseline_response, validate_phase2b_breakfix_response
from breakfix.phase2b import PHASE2B_CASE_IDS, PHASE2B_MAX_EXPERIMENTS, _evaluate_execution, _select_experiments, _targeted_outcome
from breakfix.provider import DirectProvider


ROOT = Path(__file__).resolve().parents[1]


class Phase2BContractTests(unittest.TestCase):
    def test_holdout_is_fresh_balanced_and_numeric(self):
        self.assertEqual(len(PHASE2B_CASE_IDS), 16)
        self.assertEqual(len(set(PHASE2B_CASE_IDS)), 16)
        self.assertEqual(len(list((ROOT / "benchmark" / "phase2b_holdout").iterdir())), 16)
        for case_id in PHASE2B_CASE_IDS:
            public = json.loads((ROOT / "benchmark" / "phase2b_holdout" / case_id / "public.json").read_text(encoding="utf-8"))
            self.assertEqual(public["id"], case_id)
            self.assertNotIn("surface", public)

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

    def test_deepseek_pricing_uses_peak_schedule_and_cache_usage(self):
        peak = datetime(2026, 8, 29, 2, 0, tzinfo=timezone.utc)
        cost, period, cache_status, input_rate, output_rate = DirectProvider._deepseek_cost(
            input_tokens=1000,
            output_tokens=500,
            cache_hit_tokens=400,
            cache_miss_tokens=600,
            timestamp=peak,
        )
        self.assertEqual(period, "peak")
        self.assertEqual(cache_status, "mixed")
        self.assertEqual(input_rate, 1.32)
        self.assertEqual(output_rate, 3.96)
        self.assertAlmostEqual(cost, (400 * 0.044 + 600 * 1.32 + 500 * 3.96) / 1_000_000)

    def test_deepseek_request_uses_thinking_without_temperature(self):
        provider = object.__new__(DirectProvider)
        provider.provider = "deepseek"
        provider.model = "deepseek-v4-pro"
        provider.reasoning_effort = "high"
        provider.max_output_tokens = 2000
        body = provider._request_body("hello")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertNotIn("temperature", body)


if __name__ == "__main__":
    unittest.main()
