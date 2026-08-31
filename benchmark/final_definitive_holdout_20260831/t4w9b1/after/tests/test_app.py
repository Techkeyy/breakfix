import unittest
import app


class AppTests(unittest.TestCase):
    def test_current_record(self):
        self.assertEqual(app.run({"state": {"version": 2, "balance": 100, "tax_rate": 0.2}}), {"tax": 20.0, "version": 2})

if __name__ == "__main__":
    unittest.main()
