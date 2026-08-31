import unittest

from app import run


class FlexibleTransitionTests(unittest.TestCase):
    def test_normal_transition_is_accepted(self):
        self.assertEqual(
            run({"events": ["reserve", "confirm"]}),
            {"sequence": "accepted", "event_count": 2},
        )

    def test_reordered_transition_is_accepted(self):
        self.assertEqual(
            run({"events": ["confirm", "reserve"]}),
            {"sequence": "accepted", "event_count": 2},
        )


if __name__ == "__main__":
    unittest.main()
