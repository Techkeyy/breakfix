import unittest

from app import run


class ReplayStabilityTests(unittest.TestCase):
    def test_first_delivery_is_accepted(self):
        self.assertEqual(
            run({"attempts": 1}),
            {"accepted": True, "attempts": 1},
        )

    def test_replay_is_accepted(self):
        self.assertEqual(
            run({"attempts": 2}),
            {"accepted": True, "attempts": 2},
        )


if __name__ == "__main__":
    unittest.main()
