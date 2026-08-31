import unittest

from app import run


class RegionalReadinessTests(unittest.TestCase):
    def test_configured_region(self):
        self.assertEqual(run({"config": {"region": "eu"}}), {"mode": "regional", "region": "eu"})


if __name__ == "__main__":
    unittest.main()
