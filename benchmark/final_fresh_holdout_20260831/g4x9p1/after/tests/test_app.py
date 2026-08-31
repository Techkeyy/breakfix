import unittest

from app import run


class ReadingDigestTests(unittest.TestCase):
    def test_digest(self):
        self.assertEqual(run({"items": [3, 6, 9]}), {"samples": 3, "mean": 6.0})


if __name__ == "__main__":
    unittest.main()
