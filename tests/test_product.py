import json
import tempfile
import unittest
from pathlib import Path

from breakfix.git_project import ChangeSnapshot
from breakfix.fixes import apply_fix, verify_fix
from breakfix.product import analyze_change, reproduce
from breakfix.provider import ProviderAttempt, ProviderResponse, StructuredProviderResult


class FakeProvider:
    provider = "test"
    model = "test-model"
    reasoning_effort = "high"

    def complete_structured(self, _prompt, *, validator, max_recovery_attempts):
        parsed = {
            "change_summary": "average assumes a non-empty collection",
            "assumptions": [{
                "id": "A1",
                "statement": "the collection is non-empty",
                "surface": "input",
                "risk": "high",
                "evidence": [{"file": "app.py", "location": "run", "reason": "division by len"}],
                "failure_if_false": "the change raises",
                "experiment": {
                    "type": "input_empty",
                    "target": "app.py:run",
                    "hypothesis": "the collection is non-empty",
                    "perturbation": {"items": []},
                    "observable": "captured target exception or structured result",
                    "failure_predicate": "the target raises when the input collection is empty",
                    "structured_failure_predicate": None,
                    "why_this_probe_tests_this_assumption": "an empty collection directly exercises the len boundary",
                    "parameters": {},
                },
            }],
        }
        response = ProviderResponse(
            response_text='{"change_summary":"x","assumptions":[]}',
            reasoning_text="short reasoning",
            provider=self.provider,
            model=self.model,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            latency_ms=1,
            monetary_cost_usd=0,
            finish_reason="stop",
        )
        return StructuredProviderResult(True, parsed, response, None, (ProviderAttempt(1, response, None, None),))


class ProductLoopTests(unittest.TestCase):
    def test_analysis_runs_targeted_probe_generates_regression_and_reproduces(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "app.py").write_text(
                "def run(payload):\n    return {'average': sum(payload['items']) / len(payload['items'])}\n",
                encoding="utf-8",
            )
            tests = project / "tests"
            tests.mkdir()
            (tests / "test_app.py").write_text(
                "import unittest, app\nclass TestApp(unittest.TestCase):\n    def test_normal(self): self.assertEqual(app.run({'items':[1,2,3]}), {'average':2.0})\n",
                encoding="utf-8",
            )
            snapshot = ChangeSnapshot(
                project_root=project,
                change_kind="test",
                reference=None,
                diff="-return total\n+return total / len(items)\n",
                changed_files=("app.py",),
                task="Expose an average.",
                test_command="python -m unittest discover -s tests -v",
            )
            evidence = project / "evidence" / "analysis-test"
            result = analyze_change(snapshot, evidence, provider=FakeProvider())
            self.assertEqual(result.outcome, "CONFIRMED BREAK")
            self.assertEqual(result.selected_experiments, ("input_empty",))
            self.assertTrue(result.regression_valid)
            replay = reproduce(evidence)
            self.assertTrue(replay["reproduced"])

    def test_approval_gated_patch_application_and_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "app.py").write_text(
                "def run(payload):\n    return {'average': sum(payload['items']) / len(payload['items'])}\n",
                encoding="utf-8",
            )
            tests = project / "tests"
            tests.mkdir()
            (tests / "test_app.py").write_text(
                "import unittest, app\nclass TestApp(unittest.TestCase):\n    def test_normal(self): self.assertEqual(app.run({'items':[1,2,3]}), {'average':2.0})\n",
                encoding="utf-8",
            )
            snapshot = ChangeSnapshot(
                project_root=project,
                change_kind="test",
                reference=None,
                diff="-return total\n+return total / len(items)\n",
                changed_files=("app.py",),
                task="Expose an average.",
                test_command="python -m unittest discover -s tests -v",
            )
            evidence = project / "evidence" / "fix-test"
            analysis = analyze_change(snapshot, evidence, provider=FakeProvider())
            self.assertEqual(analysis.outcome, "CONFIRMED BREAK")
            with self.assertRaises(PermissionError):
                apply_fix(evidence)
            (evidence / "fix").mkdir(exist_ok=True)
            (evidence / "fix" / "proposal.json").write_text(json.dumps({
                "status": "PROPOSED",
                "causal_contract": {
                    "valid": True,
                    "confirmed_experiment_id": "input_empty",
                    "evidence_reference": "input_empty: captured target exception on an empty collection",
                    "causal_explanation": "The confirmed empty-collection exception is caused by division by len(items); guarding that boundary removes the cause.",
                },
                "proposal": {
                    "summary": "guard the empty boundary",
                    "patch": """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@
 def run(payload):
-    return {'average': sum(payload['items']) / len(payload['items'])}
+    items = payload['items']
+    if not items:
+        return {'average': None}
+    return {'average': sum(items) / len(items)}
""",
                    "files_changed": ["app.py"],
                    "tests_to_run": ["python -m unittest discover -s tests -v"],
                    "evidence_reference": "input_empty: captured target exception on an empty collection",
                    "causal_explanation": "The confirmed empty-collection exception is caused by division by len(items); guarding that boundary removes the cause.",
                },
            }), encoding="utf-8")
            applied = apply_fix(evidence, approved=True)
            self.assertTrue(applied["applied"])
            verified = verify_fix(evidence)
            self.assertEqual(verified["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
