import unittest

from app import run


class TelemetryScaleTests(unittest.TestCase):
    def test_nonzero_sample_is_scaled(self):
        self.assertEqual(
            run({"items": [6, 9]}),
            {"state": "normalised", "value": 7},
        )


if __name__ == "__main__":
    unittest.main()
