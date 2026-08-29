import unittest
import app

class DeliveryTests(unittest.TestCase):
    def test_one_delivery(self):
        self.assertEqual(app.run({"request_id":"a","amount":25}), {"accepted":1,"effects":1})

if __name__ == "__main__":
    unittest.main()
