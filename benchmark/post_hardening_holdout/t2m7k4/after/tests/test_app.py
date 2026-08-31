import unittest

from app import run


class AccountSnapshotTests(unittest.TestCase):
    def test_current_state_is_reported(self):
        self.assertEqual(
            run({"state": {"version": 2, "tax_rate": 0.2}}),
            {"version": 2, "tax": 0.2},
        )


if __name__ == "__main__":
    unittest.main()
