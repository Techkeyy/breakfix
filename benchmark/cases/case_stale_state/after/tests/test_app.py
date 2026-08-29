import unittest

import app


class TotalTests(unittest.TestCase):
    def test_current_state_total(self):
        self.assertEqual(app.run({"state": {"version": 2, "balance": 100, "tax_rate": 0.2}}), {"total": 120.0})


if __name__ == "__main__":
    unittest.main()

