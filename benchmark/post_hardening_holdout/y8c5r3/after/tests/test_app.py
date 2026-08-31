import unittest

from app import run


class AccountMetadataTests(unittest.TestCase):
    def test_current_state_is_reported(self):
        self.assertEqual(
            run({"state": {"version": 2, "tax_rate": 0.2}}),
            {"version": 2, "tax": 0.2},
        )

    def test_legacy_state_uses_the_default_tax(self):
        self.assertEqual(
            run({"state": {"version": 1, "balance": 100}}),
            {"version": 1, "tax": 0},
        )


if __name__ == "__main__":
    unittest.main()
