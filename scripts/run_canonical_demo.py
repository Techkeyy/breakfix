from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from breakfix.diffing import make_diff
from breakfix.fixes import apply_fix, propose_fix, verify_fix
from breakfix.git_project import ChangeSnapshot
from breakfix.product import analyze_change, reproduce
from breakfix.provider import ProviderAttempt, ProviderResponse, StructuredProviderResult


class RecordedPlanner:
    """Deterministic demo provider double; the product still executes the loop."""

    provider = "recorded-demo"
    model = "recorded-demo-planner"
    reasoning_effort = "high"

    def complete_structured(self, _prompt, *, validator, max_recovery_attempts):
        parsed = {
            "change_summary": "mean calculation assumes a non-empty collection",
            "assumptions": [
                {
                    "id": "A1",
                    "statement": "the selected change receives at least one item",
                    "surface": "input",
                    "risk": "high",
                    "evidence": [
                        {
                            "file": "app.py",
                            "location": "run",
                            "reason": "division by len(items)",
                        }
                    ],
                    "failure_if_false": "the changed function raises",
                    "experiment": {"type": "input_empty", "parameters": {}},
                }
            ],
        }
        response = ProviderResponse(
            response_text=json.dumps(parsed),
            reasoning_text="recorded demo planning trace",
            provider=self.provider,
            model=self.model,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            latency_ms=1,
            monetary_cost_usd=0,
            finish_reason="stop",
            response_format="json_object",
        )
        return StructuredProviderResult(
            True,
            parsed,
            response,
            None,
            (ProviderAttempt(1, response, None, None),),
        )


class RecordedFixProvider:
    """Deterministic reviewed patch fixture for a reliable local demo."""

    provider = "recorded-demo"
    model = "recorded-demo-fixer"
    reasoning_effort = "high"

    def complete_structured(self, _prompt, *, validator, max_recovery_attempts):
        parsed = {
            "summary": "guard the mean calculation for an empty collection",
            "patch": (
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def run(payload):\n"
                "     items = payload[\"items\"]\n"
                "-    return {\"count\": len(items), \"mean\": sum(items) / len(items)}\n"
                "+    mean = sum(items) / len(items) if items else 0\n"
                "+    return {\"count\": len(items), \"mean\": mean}\n"
            ),
            "files_changed": ["app.py"],
            "tests_to_run": ["python -m unittest discover -s tests -v"],
        }
        response = ProviderResponse(
            response_text=json.dumps(parsed),
            reasoning_text="recorded demo fix trace",
            provider=self.provider,
            model=self.model,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            latency_ms=1,
            monetary_cost_usd=0,
            finish_reason="stop",
            response_format="json_object",
        )
        return StructuredProviderResult(
            True,
            parsed,
            response,
            None,
            (ProviderAttempt(1, response, None, None),),
        )


def main() -> None:
    sample = PROJECT_ROOT / "examples" / "independent_sample"
    before = sample / "before" / "app.py"
    after = sample / "after"
    snapshot = ChangeSnapshot(
        project_root=after,
        change_kind="canonical-demo",
        reference="examples/independent_sample",
        diff=make_diff(before, after / "app.py"),
        changed_files=("app.py",),
        task="Add a mean to the summary while preserving safe behavior.",
        test_command="python -m unittest discover -s tests -v",
    )
    run_id = "canonical-demo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = PROJECT_ROOT / "evidence" / run_id
    analysis = analyze_change(snapshot, evidence, provider=RecordedPlanner())
    if analysis.outcome != "CONFIRMED BREAK" or not analysis.regression_valid:
        raise SystemExit("canonical demo analysis did not confirm a reproducible break")
    replay = reproduce(evidence)
    proposal = propose_fix(evidence, provider=RecordedFixProvider())
    if proposal.get("status") != "PROPOSED":
        raise SystemExit("canonical demo did not produce a fix proposal")
    application = apply_fix(evidence, approved=True)
    if not application.get("applied"):
        raise SystemExit("canonical demo fix application failed")
    verification = verify_fix(evidence)
    result = {
        "run_id": run_id,
        "evidence_dir": str(evidence),
        "analysis": analysis.as_dict(),
        "replay": replay,
        "proposal": {
            "status": proposal.get("status"),
            "human_approval_required": proposal.get("human_approval_required"),
        },
        "application": {
            "approved": application.get("approved"),
            "applied": application.get("applied"),
        },
        "verification": {
            "status": verification.get("status"),
            "experiment_process_failed_after_fix": verification.get("experiment", {}).get("process_failed"),
            "visible_tests_exit_code": (verification.get("visible_tests") or {}).get("exit_code"),
            "regression_exit_code": (verification.get("regression") or {}).get("exit_code"),
        },
    }
    (evidence / "canonical-demo-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    if verification.get("status") != "VERIFIED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
