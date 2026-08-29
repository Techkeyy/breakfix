import json
import unittest

from breakfix.agent_contract import validate_baseline_response, validate_breakfix_response


class AgentContractTests(unittest.TestCase):
    def test_baseline_response_requires_structured_findings(self):
        result = validate_baseline_response(json.dumps({"decision": "needs-review", "findings": [{"summary": "x", "evidence": ["a"]}]}))
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"][0]["summary"], "x")

    def test_malformed_breakfix_response_is_not_executable(self):
        result = validate_breakfix_response("not json")
        self.assertFalse(result["valid"])
        self.assertEqual(result["selected_experiment_ids"], [])

    def test_unsupported_experiment_is_recorded_and_not_selected(self):
        result = validate_breakfix_response(json.dumps({
            "change_summary": "change",
            "assumptions": [{
                "id": "a",
                "statement": "s",
                "surface": "input",
                "evidence": ["app.py:1"],
                "failure_if_false": "f",
                "risk": "high",
                "proposed_experiment": {"id": "invented_probe"},
            }],
        }))
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_experiment_ids"], [])
        self.assertEqual(result["unsupported_assumptions"][0]["proposed_experiment"]["id"], "invented_probe")

    def test_duplicate_supported_experiments_are_deduplicated(self):
        assumption = {
            "id": "a",
            "statement": "s",
            "surface": "world",
            "evidence": ["app.py:1"],
            "failure_if_false": "f",
            "risk": "medium",
            "proposed_experiment": {"id": "world_dst"},
        }
        result = validate_breakfix_response(json.dumps({"change_summary": "change", "assumptions": [assumption, {**assumption, "id": "b"}]}))
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_experiment_ids"], ["world_dst"])


if __name__ == "__main__":
    unittest.main()
