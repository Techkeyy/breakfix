import unittest
import app

class ScheduleTests(unittest.TestCase):
    def test_daytime(self):
        self.assertEqual(app.run({"timestamp":"2026-01-15T15:00:00+00:00","timezone":"America/New_York"}), {"open":True})

if __name__ == "__main__":
    unittest.main()
