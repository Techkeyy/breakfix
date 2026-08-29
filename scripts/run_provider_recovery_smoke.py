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
from breakfix.provider import DirectProvider


DEV_CASES = (
    ("case_01", "faulty development case"),
    ("case_05", "safe control development case"),
)


def _snapshot(case_root: Path) -> ChangeSnapshot:
    public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
    after = case_root / "after"
    return ChangeSnapshot(
        project_root=after,
        change_kind="development-case",
        reference=public["id"],
        diff=make_diff(case_root / "before" / "app.py", after / "app.py"),
        changed_files=("app.py",),
        task=public["task"],
        test_command=public["test_command"],
    )


def main() -> None:
    provider = DirectProvider()
    if provider.provider != "deepseek":
        raise SystemExit("Recovery smoke requires the authorized DeepSeek provider")
    if not provider.api_key:
        raise SystemExit(f"Recovery smoke preflight failed: set {provider.api_key_env}")
    run_id = "provider-recovery-smoke-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root = PROJECT_ROOT / "evidence" / run_id
    results = []
    for case_id, role in DEV_CASES:
        case_root = PROJECT_ROOT / "benchmark" / "phase1_5_cases" / case_id
        result = analyze_change(
            _snapshot(case_root),
            evidence_root / case_id,
            provider=provider,
            max_experiments=3,
            max_recovery_attempts=1,
        )
        result_dict = {"case_id": case_id, "role": role, **result.as_dict()}
        results.append(result_dict)

    faulty = next(item for item in results if item["case_id"] == "case_01")
    control = next(item for item in results if item["case_id"] == "case_05")
    checks = {
        "both_provider_contracts_passed": all(item["provider_status"] == "OK" for item in results),
        "both_selected_assumptions": all(bool(item["selected_experiments"]) for item in results),
        "both_executed_targeted_experiments": all(item["experiments_run"] > 0 for item in results),
        "faulty_case_confirmed_break": faulty["outcome"] == "CONFIRMED BREAK",
        "faulty_case_regression_valid": faulty["regression_valid"] is True,
        "control_not_confirmed_break": control["outcome"] != "CONFIRMED BREAK",
        "telemetry_and_evidence_written": all(
            (evidence_root / item["case_id"] / "provider-telemetry.json").is_file()
            and (evidence_root / item["case_id"] / "analysis.json").is_file()
            for item in results
        ),
    }
    summary = {
        "run_id": run_id,
        "purpose": "engineering provider-contract gate; not benchmark evidence",
        "provider": provider.provider,
        "model": provider.model,
        "reasoning_effort": provider.reasoning_effort,
        "cases": results,
        "checks": checks,
        "passed": all(checks.values()),
    }
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / "smoke-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Provider recovery smoke: {'PASS' if summary['passed'] else 'FAIL'}")
    print(f"Run: {run_id}")
    for item in results:
        print(f"{item['case_id']}: outcome={item['outcome']} experiments={item['experiments_run']} provider={item['provider_status']}")
    print(f"Evidence: evidence/{run_id}")
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
