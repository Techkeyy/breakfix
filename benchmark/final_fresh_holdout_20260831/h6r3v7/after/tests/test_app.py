import unittest

from app import run


class FirstReadingTests(unittest.TestCase):
    def test_positive_reading(self):
        self.assertEqual(run({"items": [7]}), {"value": 7, "source": "first"})


if __name__ == "__main__":
    unittest.main()
