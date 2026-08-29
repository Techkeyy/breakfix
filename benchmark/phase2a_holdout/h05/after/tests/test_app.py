import unittest

import app


class AccountTests(unittest.TestCase):
    def test_current_record(self):
        self.assertEqual(app.run({"state": {"balance": 42}}), {"balance": 42})


if __name__ == "__main__":
    unittest.main()
