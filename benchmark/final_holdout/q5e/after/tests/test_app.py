import unittest
import app


class VisibleTests(unittest.TestCase):
    def test_normal_context(self):
        self.assertEqual(app.run({"amount": 25, "attempts": 1}), {'total_charged': 25})


if __name__ == "__main__":
    unittest.main()
