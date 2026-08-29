import unittest

import app


class ClaimTests(unittest.TestCase):
    def test_single_claim(self):
        self.assertEqual(app.run({"request_id": "x", "amount": 25}), {"accepted": 1, "effects": 1})


if __name__ == "__main__":
    unittest.main()
