import json
import tempfile
import unittest
from pathlib import Path

from breakfix.remote_api import JobManager, normalize_repository_url, public_evidence, validate_job_request


class RemoteApiContractTests(unittest.TestCase):
    def test_public_repository_url_validation(self):
        self.assertEqual(normalize_repository_url("https://github.com/Techkeyy/breakfix.git"), "https://github.com/Techkeyy/breakfix.git")
        with self.assertRaises(ValueError):
            normalize_repository_url("http://github.com/Techkeyy/breakfix")
        with self.assertRaises(ValueError):
            normalize_repository_url("https://github.com/Techkeyy/breakfix?token=secret")

    def test_demo_is_limited_to_canonical_public_repository(self):
        request = validate_job_request({"repository_url": "https://github.com/Techkeyy/breakfix", "demo": True})
        self.assertTrue(request["demo"])
        with self.assertRaises(ValueError):
            validate_job_request({"repository_url": "https://github.com/example/other", "demo": True})

    def test_non_demo_requires_safe_git_reference(self):
        request = validate_job_request({"repository_url": "https://github.com/example/project", "change": {"kind": "commit", "reference": "abc123"}})
        self.assertEqual(request["change"]["reference"], "abc123")
        with self.assertRaises(ValueError):
            validate_job_request({"repository_url": "https://github.com/example/project", "change": {"kind": "commit", "reference": "--upload-pack=x"}})

    def test_request_body_is_not_allowed_to_change_experiment_budget(self):
        request = validate_job_request({"repository_url": "https://github.com/example/project", "change": {"kind": "commit", "reference": "abc123"}, "max_experiments": 99})
        self.assertNotIn("max_experiments", request)

    def test_public_evidence_omits_paths_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "analysis.json").write_text(json.dumps({"outcome": "CONFIRMED BREAK", "project_root": "/secret", "experiment_records": [{"experiment_id": "input_empty", "actual_behavior": {"process_failed": True, "output": {"count": 0}}, "evidence_path": "/secret"}]}), encoding="utf-8")
            (root / "planner.json").write_text(json.dumps({"assumptions": []}), encoding="utf-8")
            value = public_evidence(root, "00000000-0000-0000-0000-000000000000")
            encoded = json.dumps(value)
            self.assertIn("CONFIRMED BREAK", encoded)
            self.assertNotIn("project_root", encoded)
            self.assertNotIn("evidence_path", encoded)
            self.assertNotIn("/secret", encoded)

    def test_job_manager_uses_a_bounded_single_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = JobManager(Path(temporary))
            self.assertEqual(manager.executor._max_workers, 1)
            manager.executor.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
