import unittest
import app

class LedgerTests(unittest.TestCase):
    def test_one_request(self):
        self.assertEqual(app.run({"request_id":"a"}), {"accepted":1})

if __name__ == "__main__":
    unittest.main()
