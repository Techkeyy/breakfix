import unittest
import app


class SummaryTests(unittest.TestCase):
    def test_normal_items(self):
        self.assertEqual(app.run({"items": [2, 4, 6]}), {"count": 3, "mean": 4.0})


if __name__ == "__main__":
    unittest.main()
