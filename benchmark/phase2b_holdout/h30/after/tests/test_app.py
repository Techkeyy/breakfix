import unittest
import app

class MetricTests(unittest.TestCase):
    def test_positive_values(self):
        self.assertEqual(app.run({"items":[10,20]}), {"total":30,"count":2,"mean":15.0})

if __name__ == "__main__":
    unittest.main()
