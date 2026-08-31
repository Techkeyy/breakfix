import unittest

from app import run


class SensorReadingTests(unittest.TestCase):
    def test_zero_reading(self):
        self.assertEqual(run({"items": [0]}), {"reading": 0, "present": True})


if __name__ == "__main__":
    unittest.main()
