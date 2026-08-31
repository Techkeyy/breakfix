import unittest

from app import run


class ZoneMetadataTests(unittest.TestCase):
    def test_named_zone(self):
        self.assertEqual(run({"timezone": "America/New_York", "timestamp": "2026-01-15T19:00:00+00:00"}), {"zone": "America/New_York", "offset_mode": "named"})


if __name__ == "__main__":
    unittest.main()
