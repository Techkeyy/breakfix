import unittest
import app


class VisibleTests(unittest.TestCase):
    def test_normal_context(self):
        self.assertEqual(app.run({"concurrent_calls": 1}), {'accepted': 1})


if __name__ == "__main__":
    unittest.main()
