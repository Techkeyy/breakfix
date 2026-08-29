import unittest
import app


class VisibleTests(unittest.TestCase):
    def test_normal_context(self):
        self.assertEqual(app.run({"events": ["reserve", "confirm"]}), {'status': 'confirmed'})


if __name__ == "__main__":
    unittest.main()
