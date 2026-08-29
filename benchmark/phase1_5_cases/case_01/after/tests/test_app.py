import unittest

import app


class SummaryTests(unittest.TestCase):
    def test_average_for_normal_collection(self):
        self.assertEqual(app.run({"items": [1, 2, 3]}), {"count": 3, "average": 2.0})


if __name__ == "__main__":
    unittest.main()

