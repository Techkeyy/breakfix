import unittest
import app


class AppTests(unittest.TestCase):
    def test_regular_collection(self):
        self.assertEqual(app.run({"items": [3, 9]}), {"average": 6.0, "count": 2})

if __name__ == "__main__":
    unittest.main()
