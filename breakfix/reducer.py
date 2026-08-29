from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .evidence import write_json
from .executor import run_experiment_isolated


def reduce_reproduction(evidence_dir: Path) -> dict[str, Any]:
    """Try a bounded one-dimension-at-a-time reduction of a confirmed probe."""
    root = evidence_dir.resolve()
    analysis = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
    confirmed = next(
        (record for record in analysis.get("experiment_records", []) if record.get("evidence_state") == "CONFIRMED BREAK"),
        None,
    )
    if confirmed is None:
        raise RuntimeError("evidence does not contain a confirmed break to reduce")
    original = confirmed["payload"]
    candidates = []
    for key in sorted(original):
        if key in {"request_id", "state", "events", "items"}:
            candidate = deepcopy(original)
            candidate.pop(key, None)
            candidates.append((key, candidate))
    attempts = []
    reduced = original
    for removed_key, candidate in candidates[:4]:
        execution = run_experiment_isolated(
            Path(analysis.get("project_snapshot") or analysis["project_root"]),
            confirmed["experiment_id"],
            candidate,
        )
        attempt = {
            "removed_key": removed_key,
            "payload": candidate,
            "process_failed": execution.process_failed,
            "output": execution.output,
            "stderr": execution.stderr,
        }
        attempts.append(attempt)
        if execution.process_failed:
            reduced = candidate
            break
    result = {
        "status": "REDUCED REPRODUCTION" if reduced != original else "NO REDUCTION FOUND",
        "minimality_claim": False,
        "experiment_id": confirmed["experiment_id"],
        "original_payload": original,
        "reduced_payload": reduced,
        "attempts": attempts,
    }
    write_json(root / "reduction.json", result)
    return result
