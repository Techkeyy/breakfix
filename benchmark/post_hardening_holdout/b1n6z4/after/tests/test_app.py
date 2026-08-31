import unittest

from app import run


class ReadinessEnvelopeTests(unittest.TestCase):
    def test_configured_request_is_regional(self):
        self.assertEqual(
            run({"config": {"currency": "USD"}}),
            {"mode": "regional", "region": "global"},
        )


if __name__ == "__main__":
    unittest.main()
