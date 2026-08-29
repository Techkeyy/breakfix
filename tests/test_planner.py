import unittest

from breakfix.experiments import experiment_by_id
from breakfix.planner import infer_assumptions, targeted_experiments


class PlannerTests(unittest.TestCase):
    def test_input_diff_selects_input_probes(self):
        diff = "-return total\n+return total / len(items)\n"
        assumptions = infer_assumptions(diff)
        self.assertEqual(assumptions[0].surface, "input")
        self.assertIn("input_empty", targeted_experiments(assumptions))

    def test_replay_diff_selects_duplicate_probe(self):
        diff = "-if request_id not in _processed:\n+_processed.add(request_id)\n+for _ in range(payload.get('attempts', 1)):\n"
        selected = targeted_experiments(infer_assumptions(diff))
        self.assertEqual(selected, ["retry_duplicate"])
        self.assertEqual(experiment_by_id(selected[0]).surface, "timing")

    def test_unrelated_diff_does_not_create_assumption(self):
        self.assertEqual(infer_assumptions("-return 1\n+return 2\n"), [])


if __name__ == "__main__":
    unittest.main()

