import unittest

from app import run


class StableReadinessTests(unittest.TestCase):
    def test_configured_request_is_regional(self):
        self.assertEqual(
            run({"config": {"currency": "USD"}}),
            {"mode": "regional", "region": "global"},
        )

    def test_empty_config_uses_the_default_region(self):
        self.assertEqual(
            run({"config": {}}),
            {"mode": "regional", "region": "global"},
        )


if __name__ == "__main__":
    unittest.main()
