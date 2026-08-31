import unittest

from app import run


class ReplayHandlingTests(unittest.TestCase):
    def test_replayed_delivery(self):
        self.assertEqual(run({"attempts": 2}), {"status": "accepted", "replays": 1})


if __name__ == "__main__":
    unittest.main()
