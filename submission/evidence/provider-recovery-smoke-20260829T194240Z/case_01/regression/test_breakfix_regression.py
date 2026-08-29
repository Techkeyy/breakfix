import unittest
import app


class BreakFixRegressionTests(unittest.TestCase):
    def test_observed_change_handles_targeted_perturbation(self):
        payload = '{"amount": 25, "attempts": 1, "concurrent_calls": 1, "config": {"currency": "USD"}, "events": ["reserve", "confirm"], "items": [], "request_id": "charge-001", "state": {"tax_rate": 0.2, "version": 2}, "timestamp": "2026-01-15T19:00:00+00:00", "timezone": "America/New_York"}'
        result = app.run(payload)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
