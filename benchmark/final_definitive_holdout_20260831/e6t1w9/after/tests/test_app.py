import unittest
import app


class AppTests(unittest.TestCase):
    def test_winter_timestamp(self):
        self.assertEqual(app.run({"timestamp": "2026-01-15T19:00:00+00:00", "timezone": "America/New_York"}), {"offset_mode": "named", "zone": "America/New_York", "calendar": "standard"})

if __name__ == "__main__":
    unittest.main()
