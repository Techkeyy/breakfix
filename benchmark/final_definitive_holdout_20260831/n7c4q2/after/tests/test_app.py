import unittest
import app


class AppTests(unittest.TestCase):
    def test_regular_collection(self):
        self.assertEqual(app.run({"items": [2, 4]}), {"average": 3.0, "count": 2})

if __name__ == "__main__":
    unittest.main()
