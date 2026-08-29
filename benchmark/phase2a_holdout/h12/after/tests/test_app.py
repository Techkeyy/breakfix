import unittest

import app


class ConfigTests(unittest.TestCase):
    def test_explicit_currency(self):
        self.assertEqual(app.run({"config": {"currency": "EUR"}}), {"currency": "EUR"})


if __name__ == "__main__":
    unittest.main()
