import unittest

from app import run


class EventOrderingTests(unittest.TestCase):
    def test_reordered_delivery(self):
        self.assertEqual(run({"events": ["confirm", "reserve"]}), {"sequence": "accepted", "event_count": 2})


if __name__ == "__main__":
    unittest.main()
