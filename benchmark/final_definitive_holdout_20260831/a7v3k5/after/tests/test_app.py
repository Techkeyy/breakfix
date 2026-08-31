import unittest
import app


class AppTests(unittest.TestCase):
    def test_single_request(self):
        self.assertEqual(app.run({"attempts": 1}), {"accepted": True, "attempts": 1, "replays": 0, "status": "accepted"})

if __name__ == "__main__":
    unittest.main()
