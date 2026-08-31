import unittest

from app import run


class RegionalSettingsTests(unittest.TestCase):
    def test_default_region(self):
        self.assertEqual(run({"config": {"currency": "USD"}}), {"mode": "regional", "region": "global"})


if __name__ == "__main__":
    unittest.main()
