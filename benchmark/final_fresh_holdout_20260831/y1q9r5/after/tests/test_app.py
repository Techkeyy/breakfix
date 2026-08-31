import unittest

from app import run


class CalendarMarkerTests(unittest.TestCase):
    def test_regular_calendar(self):
        self.assertEqual(run({"timezone": "America/New_York", "timestamp": "2026-01-15T19:00:00+00:00"}), {"zone": "America/New_York", "calendar": "regional"})


if __name__ == "__main__":
    unittest.main()
