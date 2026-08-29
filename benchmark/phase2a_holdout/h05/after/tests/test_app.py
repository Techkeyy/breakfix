import unittest

import app


class AccountTests(unittest.TestCase):
    def test_current_record(self):
        self.assertEqual(app.run({"state": {"tax_rate": 0.2}}), {"tax_rate": 0.2})


if __name__ == "__main__":
    unittest.main()
