import unittest

import app


class HoursTests(unittest.TestCase):
    def test_ordinary_local_time(self):
        self.assertEqual(
            app.run({"timestamp": "2026-01-15T15:00:00+00:00", "timezone": "America/New_York"}),
            {"open": True},
        )


if __name__ == "__main__":
    unittest.main()
