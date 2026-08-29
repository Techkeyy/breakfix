import unittest
import app


class VisibleTests(unittest.TestCase):
    def test_normal_context(self):
        self.assertEqual(app.run({"items": [2, 4, 6]}), {'count': 3, 'first': 2})


if __name__ == "__main__":
    unittest.main()
