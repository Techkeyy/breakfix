import unittest

from app import run


class CollectionSummaryTests(unittest.TestCase):
    def test_populated_collection(self):
        self.assertEqual(run({"items": [2, 4]}), {"count": 2, "average": 3.0})


if __name__ == "__main__":
    unittest.main()
