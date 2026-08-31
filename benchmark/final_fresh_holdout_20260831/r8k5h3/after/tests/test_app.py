import unittest

from app import run


class RepeatDeliveryTests(unittest.TestCase):
    def test_first_delivery(self):
        self.assertEqual(run({"attempts": 1}), {"accepted": True, "attempts": 1})


if __name__ == "__main__":
    unittest.main()
