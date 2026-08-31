import unittest

from app import run


class ReadingCatalogueTests(unittest.TestCase):
    def test_regular_batch_is_catalogued(self):
        self.assertEqual(
            run({"items": [4, 8, 12]}),
            {"state": "catalogued", "sample_count": 3},
        )


if __name__ == "__main__":
    unittest.main()
