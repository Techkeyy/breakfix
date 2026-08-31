import unittest
import app


class AppTests(unittest.TestCase):
    def test_current_configuration(self):
        self.assertEqual(app.run({"config": {"mode": "regional", "region": "eu"}}), {"mode": "regional", "region": "eu"})

if __name__ == "__main__":
    unittest.main()
