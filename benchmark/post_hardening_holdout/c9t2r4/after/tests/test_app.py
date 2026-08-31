import unittest

from app import run


class StableZoneTests(unittest.TestCase):
    def test_regular_timestamp_keeps_named_zone(self):
        self.assertEqual(
            run({"timestamp": "2026-01-15T19:00:00+00:00", "timezone": "America/New_York"}),
            {"zone": "America/New_York", "offset_mode": "named"},
        )

    def test_boundary_timestamp_keeps_named_zone(self):
        self.assertEqual(
            run({"timestamp": "2026-03-29T20:30:00+00:00", "timezone": "America/New_York"}),
            {"zone": "America/New_York", "offset_mode": "named"},
        )


if __name__ == "__main__":
    unittest.main()
