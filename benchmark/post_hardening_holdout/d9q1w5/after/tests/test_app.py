import unittest

from app import run


class StableScaleTests(unittest.TestCase):
    def test_nonzero_sample_is_scaled(self):
        self.assertEqual(
            run({"items": [6, 9]}),
            {"state": "normalised", "value": 7},
        )

    def test_zero_sample_is_stable(self):
        self.assertEqual(
            run({"items": [0]}),
            {"state": "normalised", "value": 0},
        )


if __name__ == "__main__":
    unittest.main()
