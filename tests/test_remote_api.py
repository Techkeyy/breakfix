import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from breakfix.remote_api import JobManager, normalize_repository_url, public_evidence, readiness, validate_job_request
from breakfix.evidence import write_json


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

    def test_provider_error_evidence_is_always_failed_and_not_terminal_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "analysis.json").write_text(json.dumps({
                "outcome": "ERROR",
                "error_code": "PROVIDER_ERROR",
                "experiments_run": 0,
            }), encoding="utf-8")
            evidence = public_evidence(root, "00000000-0000-0000-0000-000000000000", {"status": "COMPLETED"})
            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(evidence["outcome"], "ERROR")

    def test_job_manager_marks_provider_error_failed_with_not_run_stages(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = JobManager(Path(temporary))
            request = validate_job_request({"repository_url": "https://github.com/Techkeyy/breakfix", "demo": True})

            def fake_clone(job_id, _request):
                project = manager._directory(job_id) / "project"
                project.mkdir()
                return project

            def fake_docker(job_id, _mode, **_kwargs):
                write_json(manager._directory(job_id) / "evidence" / "analysis.json", {
                    "outcome": "ERROR",
                    "provider_status": "PROVIDER_ERROR",
                    "error_code": "PROVIDER_ERROR",
                    "experiments_run": 0,
                })

            with patch.object(manager, "_clone", side_effect=fake_clone), patch.object(manager, "_docker", side_effect=fake_docker):
                created = manager.create(request)
                manager.executor.shutdown(wait=True)
            record = manager.get(created["job_id"])
            self.assertEqual(record["status"], "FAILED")
            self.assertEqual(record["result"]["status"], "FAILED")
            self.assertEqual(record["stages"]["finding_assumptions"], "failed")
            self.assertEqual(record["stages"]["selecting_experiments"], "not_run")
            self.assertEqual(record["stages"]["executing"], "not_run")
            self.assertIn("no experiments", record["error"].lower())

    def test_readiness_is_secret_free_and_reports_degraded_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = JobManager(Path(temporary))
            with patch("breakfix.remote_api.shutil.which", return_value="/usr/bin/docker"), patch(
                "breakfix.remote_api._bounded_run",
                return_value=type("Result", (), {"returncode": 0})(),
            ), patch("breakfix.remote_api._provider_network_reachable", return_value=False):
                status, payload = readiness(manager)
            self.assertEqual(status, 503)
            self.assertEqual(payload["status"], "degraded")
            self.assertIn("provider_credential_present", payload["checks"])
            self.assertNotIn("api_key", json.dumps(payload).lower())
            manager.executor.shutdown(wait=True)

    def test_job_manager_uses_a_bounded_single_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = JobManager(Path(temporary))
            self.assertEqual(manager.executor._max_workers, 1)
            manager.executor.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
