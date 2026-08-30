import unittest

from breakfix.benchmark import after_dir, load_cases
from breakfix.executor import run_experiment
from breakfix.experiments import experiment_by_id, payload_for


class BenchmarkContractTests(unittest.TestCase):
    def setUp(self):
        from pathlib import Path

        self.root = Path(__file__).resolve().parents[1]

    def test_five_public_cases_are_frozen(self):
        cases = load_cases(self.root)
        self.assertEqual(len(cases), 5)
        self.assertEqual(
            {case["id"] for case in cases},
            {
                "case_input_boundary",
                "case_retry_duplicate",
                "case_stale_state",
                "case_reordered_events",
                "case_timezone_robust",
            },
        )

    def test_empty_input_is_observable_as_a_process_failure(self):
        experiment = experiment_by_id("input_empty")
        result = run_experiment(
            after_dir(self.root, "case_input_boundary"),
            experiment.id,
            payload_for(experiment),
        )
        self.assertTrue(result.process_failed)
        self.assertIn("ZeroDivisionError", result.stderr)

    def test_reordered_events_is_an_output_mismatch_without_a_crash(self):
        experiment = experiment_by_id("events_reordered")
        result = run_experiment(
            after_dir(self.root, "case_reordered_events"),
            experiment.id,
            payload_for(experiment),
        )
        self.assertFalse(result.process_failed)
        self.assertEqual(result.output, {"status": "pending"})


if __name__ == "__main__":
    unittest.main()
