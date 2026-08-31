import unittest

from app import run


class CalendarContextTests(unittest.TestCase):
    def test_boundary_context(self):
        self.assertEqual(run({"timezone": "America/New_York", "timestamp": "2026-03-29T20:30:00+00:00"}), {"zone": "America/New_York", "calendar": "regional"})


if __name__ == "__main__":
    unittest.main()
