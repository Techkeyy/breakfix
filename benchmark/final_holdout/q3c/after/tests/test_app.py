import unittest
import app


class VisibleTests(unittest.TestCase):
    def test_normal_context(self):
        self.assertEqual(app.run({"state": {"balance": 100, "tax_rate": 0.2, "version": 2}}), {'total': 120.0})


if __name__ == "__main__":
    unittest.main()
