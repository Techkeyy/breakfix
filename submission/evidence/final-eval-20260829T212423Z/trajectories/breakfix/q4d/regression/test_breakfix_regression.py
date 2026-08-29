import unittest
import app


class BreakFixRegressionTests(unittest.TestCase):
    def test_observed_change_handles_targeted_perturbation(self):
        payload = {'items': [10, 20, 30], 'request_id': 'charge-001', 'amount': 25, 'attempts': 1, 'state': {'version': 2, 'tax_rate': 0.2}, 'events': ['reserve', 'confirm'], 'timestamp': '2026-01-15T19:00:00+00:00', 'timezone': 'America/New_York', 'config': {}, 'concurrent_calls': 1}
        result = app.run(payload)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
