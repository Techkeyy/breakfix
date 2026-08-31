import unittest

from app import run


class BatchDescriptionTests(unittest.TestCase):
    def test_populated_batch_has_a_count(self):
        self.assertEqual(
            run({"items": [7, 11]}),
            {"state": "catalogued", "sample_count": 2},
        )

    def test_empty_batch_has_zero_count(self):
        self.assertEqual(
            run({"items": []}),
            {"state": "catalogued", "sample_count": 0},
        )


if __name__ == "__main__":
    unittest.main()
