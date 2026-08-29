import unittest

import app


class DeliveryTests(unittest.TestCase):
    def test_first_delivery_is_applied(self):
        self.assertEqual(app.run({"request_id": "x", "amount": 25}), {"total_charged": 25})


if __name__ == "__main__":
    unittest.main()
