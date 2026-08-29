import unittest

import app


class BusinessHoursTests(unittest.TestCase):
    def test_normal_business_hours(self):
        self.assertEqual(
            app.run(
                {
                    "timestamp": "2026-01-15T14:00:00+00:00",
                    "timezone": "America/New_York",
                }
            ),
            {"open": True},
        )


if __name__ == "__main__":
    unittest.main()

