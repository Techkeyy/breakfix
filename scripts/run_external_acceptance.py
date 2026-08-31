from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from breakfix.diffing import make_diff
from breakfix.git_project import ChangeSnapshot
from breakfix.product import analyze_change
from breakfix.provider import ProviderAttempt, ProviderResponse, StructuredProviderResult


class RecordedPlanner:
    """Deterministic provider double for the independent acceptance sample."""

    provider = "recorded-acceptance"
    model = "recorded-planner"
    reasoning_effort = "high"

    def complete_structured(self, _prompt, *, validator, max_recovery_attempts):
        parsed = {
            "change_summary": "mean calculation assumes a non-empty collection",
            "assumptions": [{
                "id": "A1",
                "statement": "the selected change receives at least one item",
                "surface": "input",
                "risk": "high",
                "evidence": [{"file": "app.py", "location": "run", "reason": "division by len(items)"}],
                "failure_if_false": "the changed function raises",
                "experiment": {
                    "type": "input_empty",
                    "target": "app.py:run",
                    "hypothesis": "the selected change receives at least one item",
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
            response_text=json.dumps(parsed),
            reasoning_text="recorded acceptance reasoning",
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
        return StructuredProviderResult(True, parsed, response, None, (ProviderAttempt(1, response, None, None),))


def main() -> None:
    sample = PROJECT_ROOT / "examples" / "independent_sample"
    before = sample / "before" / "app.py"
    after = sample / "after"
    snapshot = ChangeSnapshot(
        project_root=after,
        change_kind="independent-acceptance-sample",
        reference="examples/independent_sample",
        diff=make_diff(before, after / "app.py"),
        changed_files=("app.py",),
        task="Add a mean to the summary while preserving safe behavior.",
        test_command="python -m unittest discover -s tests -v",
    )
    run_id = "external-acceptance-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = analyze_change(snapshot, PROJECT_ROOT / "evidence" / run_id, provider=RecordedPlanner())
    print(json.dumps({"run_id": run_id, **result.as_dict()}, indent=2))
    if result.outcome != "CONFIRMED BREAK" or not result.regression_valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
