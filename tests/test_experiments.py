import unittest

from breakfix.experiments import EXPERIMENTS, payload_for


class ExperimentTests(unittest.TestCase):
    def test_ids_are_unique(self):
        ids = [experiment.id for experiment in EXPERIMENTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_payload_does_not_mutate_base(self):
        first = payload_for(EXPERIMENTS[0])
        first["items"].append(999)
        second = payload_for(EXPERIMENTS[0])
        self.assertNotIn(999, second["items"])


if __name__ == "__main__":
    unittest.main()

