import unittest

from app import run


class LocalCalendarTests(unittest.TestCase):
    def test_regular_timestamp_has_a_calendar(self):
        self.assertEqual(
            run({"timestamp": "2026-01-15T19:00:00+00:00", "timezone": "America/New_York"}),
            {"zone": "America/New_York", "calendar": "regional"},
        )


if __name__ == "__main__":
    unittest.main()
