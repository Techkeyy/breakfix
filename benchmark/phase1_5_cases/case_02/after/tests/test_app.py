import unittest

import app


class ChargeTests(unittest.TestCase):
    def test_single_delivery_charges_once(self):
        self.assertEqual(app.run({"request_id": "x", "amount": 25, "attempts": 1}), {"total_charged": 25})


if __name__ == "__main__":
    unittest.main()

