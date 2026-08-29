from __future__ import annotations

from typing import Any


def review_change(diff: str, visible_tests: dict[str, Any]) -> dict[str, Any]:
    """Offline stand-in for a direct generic review, deliberately no hidden probes."""
    added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    text = f"{added}\n{removed}".lower()
    findings: list[dict[str, str]] = []

    if "/ len(" in text or "max(" in text:
        findings.append({
            "severity": "medium",
            "finding": "A collection boundary may raise or produce an invalid result.",
        })
    if "state[" in added and ".get(" in removed:
        findings.append({
            "severity": "high",
            "finding": "The changed state read may reject older persisted records.",
        })
    if "_processed" in removed and "_processed" not in added:
        findings.append({
            "severity": "high",
            "finding": "The change appears to remove duplicate-operation protection.",
        })

    return {
        "agent": "generic-review-baseline",
        "implementation": "offline deterministic surrogate, no hidden experiments",
        "visible_tests_passed": visible_tests.get("exit_code") == 0,
        "decision": "needs-review" if findings else "accept",
        "findings": findings,
        "hidden_checks_run": 0,
        "limitations": [
            "This checkpoint does not call a live model.",
            "The baseline cannot prove a failure without executing a hidden perturbation.",
        ],
    }

