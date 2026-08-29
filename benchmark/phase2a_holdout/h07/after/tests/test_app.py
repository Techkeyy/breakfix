import unittest

import app


class WorkflowTests(unittest.TestCase):
    def test_happy_path(self):
        self.assertEqual(app.run({"events": ["reserve", "confirm"]}), {"status": "confirmed"})


if __name__ == "__main__":
    unittest.main()
