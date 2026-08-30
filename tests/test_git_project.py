import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from breakfix.git_project import ChangeResolutionError, ensure_change_history, load_change
from breakfix.remote_api import public_evidence


def _run(command, cwd):
    environment = os.environ.copy()
    environment.setdefault("GIT_AUTHOR_NAME", "BreakFix Test")
    environment.setdefault("GIT_AUTHOR_EMAIL", "breakfix@example.test")
    environment.setdefault("GIT_COMMITTER_NAME", "BreakFix Test")
    environment.setdefault("GIT_COMMITTER_EMAIL", "breakfix@example.test")
    return subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True, check=True).stdout.strip()


class HostedHistoryResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        _run(["git", "init", "-b", "master"], self.source)
        _run(["git", "config", "user.name", "BreakFix Test"], self.source)
        _run(["git", "config", "user.email", "breakfix@example.test"], self.source)
        self.commits = []
        for index in range(8):
            (self.source / "app.py").write_text(f"VERSION = {index}\n", encoding="utf-8")
            _run(["git", "add", "app.py"], self.source)
            _run(["git", "commit", "-m", f"version {index}"], self.source)
            self.commits.append(_run(["git", "rev-parse", "HEAD"], self.source))
        _run(["git", "branch", "legacy", self.commits[2]], self.source)
        self.shallow = self.root / "shallow"
        _run(["git", "-c", "protocol.file.allow=always", "clone", "--depth", "1", str(self.source), str(self.shallow)], self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_recent_depth_one_branch_resolves_and_reports_full_shas(self):
        snapshot = load_change(self.shallow, change_kind="branch", reference="master", ensure_history=True)
        self.assertEqual(snapshot.resolved_base, snapshot.resolved_head)
        self.assertEqual(len(snapshot.resolved_head), 40)

    def test_old_commit_is_acquired_with_bounded_deepening(self):
        snapshot = load_change(self.shallow, change_kind="commit", reference=self.commits[1], ensure_history=True)
        self.assertEqual(snapshot.resolved_head, self.commits[1])
        self.assertEqual(len(snapshot.resolved_base), 40)
        self.assertIn("VERSION = 1", snapshot.diff)

    def test_old_range_is_acquired_and_preserves_two_dot_diff(self):
        snapshot = load_change(
            self.shallow,
            change_kind="range",
            reference=f"{self.commits[0]}..{self.commits[7]}",
            ensure_history=True,
        )
        self.assertEqual(snapshot.resolved_base, self.commits[0])
        self.assertEqual(snapshot.resolved_head, self.commits[7])
        self.assertIn("VERSION = 7", snapshot.diff)

    def test_named_branch_uses_targeted_fetch_and_reports_merge_base(self):
        snapshot = load_change(self.shallow, change_kind="branch", reference="legacy", ensure_history=True)
        self.assertEqual(snapshot.resolved_head, self.commits[7])
        self.assertEqual(snapshot.resolved_base, self.commits[2])
        self.assertIn("VERSION = 7", snapshot.diff)

    def test_invalid_commit_and_range_are_translated_without_raw_git_error(self):
        for kind, reference in (("commit", "f" * 40), ("range", f"{self.commits[0]}..{'f' * 40}")):
            with self.assertRaises(ChangeResolutionError) as context:
                load_change(self.shallow, change_kind=kind, reference=reference, ensure_history=True, max_history_depth=16)
            self.assertNotIn("fatal:", str(context.exception).lower())
            self.assertIn("could not be resolved", str(context.exception))

    def test_deepening_exhaustion_is_bounded(self):
        with self.assertRaises(ChangeResolutionError) as context:
            load_change(
                self.shallow,
                change_kind="commit",
                reference=self.commits[0],
                ensure_history=True,
                max_history_depth=16,
            )
        self.assertIn("history limit", str(context.exception))

    def test_fetch_timeout_is_not_retried_unboundedly(self):
        with patch("breakfix.git_project._git_fetch", side_effect=subprocess.TimeoutExpired(["git", "fetch"], 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                ensure_change_history(
                    self.shallow,
                    change_kind="commit",
                    reference=self.commits[0],
                    max_history_depth=16,
                    max_duration_seconds=2,
                )


class PublicResolutionEvidenceTests(unittest.TestCase):
    def test_public_evidence_exposes_resolution_metadata_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "analysis.json").write_text(
                '{"outcome":"NO BREAK CONFIRMED","changed_files":["app.py"],'
                '"change_resolution":{"requested_kind":"range","requested_reference":"old..new",'
                '"resolved_base":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
                '"resolved_head":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}}',
                encoding="utf-8",
            )
            value = public_evidence(root, "00000000-0000-0000-0000-000000000000")
            self.assertEqual(value["change_resolution"]["resolved_base"], "a" * 40)
            self.assertEqual(value["changed_files"], ["app.py"])


if __name__ == "__main__":
    unittest.main()
