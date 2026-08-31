import unittest
import app


class AppTests(unittest.TestCase):
    def test_regular_reading(self):
        self.assertEqual(app.run({"items": [7]}), {"reading": 7, "present": True})

if __name__ == "__main__":
    unittest.main()
