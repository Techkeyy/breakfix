import unittest
import app

class SummaryTests(unittest.TestCase):
    def test_populated_values(self):
        self.assertEqual(app.run({"items":[3,8,5]}), {"peak":8})

if __name__ == "__main__":
    unittest.main()
