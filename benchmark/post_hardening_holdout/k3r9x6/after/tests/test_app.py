import unittest

from app import run


class ReplayMetadataTests(unittest.TestCase):
    def test_first_delivery_is_accepted(self):
        self.assertEqual(
            run({"attempts": 1}),
            {"accepted": True, "attempts": 1},
        )


if __name__ == "__main__":
    unittest.main()
