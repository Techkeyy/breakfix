import json
import unittest

from breakfix.agent_contract import validate_baseline_response, validate_breakfix_response, validate_product_planner_response


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

    def test_product_planner_contract_uses_compact_experiment_schema(self):
        result = validate_product_planner_response(json.dumps({
            "change_summary": "average now divides by collection length",
            "assumptions": [{
                "id": "A1",
                "statement": "the collection is non-empty",
                "surface": "input",
                "risk": "high",
                "evidence": [{"file": "app.py", "location": "run", "reason": "division by len"}],
                "failure_if_false": "the changed path raises",
                "experiment": {
                    "type": "input_empty",
                    "target": "app.py:run",
                    "hypothesis": "the collection is non-empty",
                    "perturbation": {"items": []},
                    "observable": "captured target exception or structured result",
                    "failure_predicate": "the target raises when the input collection is empty",
                    "why_this_probe_tests_this_assumption": "an empty collection directly exercises the len boundary",
                    "parameters": {},
                },
            }],
        }))
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_experiment_ids"], ["input_empty"])

    def test_product_planner_rejects_missing_evidence_object_shape(self):
        result = validate_product_planner_response(json.dumps({
            "change_summary": "change",
            "assumptions": [{
                "id": "A1",
                "statement": "s",
                "surface": "input",
                "risk": "high",
                "evidence": ["app.py:1"],
                "failure_if_false": "f",
                "experiment": {
                    "type": "input_empty",
                    "target": "app.py:run",
                    "hypothesis": "the collection is non-empty",
                    "perturbation": {"items": []},
                    "observable": "captured target exception or structured result",
                    "failure_predicate": "the target raises when the input collection is empty",
                    "why_this_probe_tests_this_assumption": "an empty collection directly exercises the len boundary",
                    "parameters": {},
                },
            }],
        }))
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
