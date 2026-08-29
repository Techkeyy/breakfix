import unittest

import app


class ReplayTests(unittest.TestCase):
    def test_happy_path_order(self):
        self.assertEqual(app.run({"events": ["reserve", "confirm"]}), {"status": "confirmed"})


if __name__ == "__main__":
    unittest.main()

