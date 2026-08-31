import unittest

from app import run


class AccountCompatibilityTests(unittest.TestCase):
    def test_current_record(self):
        self.assertEqual(run({"state": {"version": 2, "tax_rate": 0.2}}), {"version": 2, "tax": 0.2})


if __name__ == "__main__":
    unittest.main()
