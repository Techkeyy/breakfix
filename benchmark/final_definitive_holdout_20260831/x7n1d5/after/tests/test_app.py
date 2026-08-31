import unittest
import app


class AppTests(unittest.TestCase):
    def test_standard_sequence(self):
        self.assertEqual(app.run({"events": ["reserve", "confirm"]}), {"sequence": "accepted", "event_count": 2})

if __name__ == "__main__":
    unittest.main()
