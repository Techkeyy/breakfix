import unittest
import app


class VisibleTests(unittest.TestCase):
    def test_normal_context(self):
        self.assertEqual(app.run({"config": {"currency": "USD"}}), {'currency': 'USD'})


if __name__ == "__main__":
    unittest.main()
