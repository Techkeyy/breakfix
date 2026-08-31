import unittest

from app import run


class EventTransitionTests(unittest.TestCase):
    def test_normal_delivery_order(self):
        self.assertEqual(run({"events": ["reserve", "confirm"]}), {"sequence": "accepted", "event_count": 2})


if __name__ == "__main__":
    unittest.main()
