from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_cases(root: Path) -> list[dict[str, Any]]:
    cases_root = root / "benchmark" / "cases"
    cases = []
    for path in sorted(cases_root.glob("*/public.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


def load_ground_truth(root: Path) -> dict[str, Any]:
    configured = os.environ.get("BREAKFIX_GROUND_TRUTH_PATH")
    if not configured:
        raise RuntimeError(
            "Historical evaluator truth is external; set BREAKFIX_GROUND_TRUTH_PATH explicitly"
        )
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Historical evaluator truth file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def case_dir(root: Path, case_id: str) -> Path:
    return root / "benchmark" / "cases" / case_id


def after_dir(root: Path, case_id: str) -> Path:
    return case_dir(root, case_id) / "after"


def before_dir(root: Path, case_id: str) -> Path:
    return case_dir(root, case_id) / "before"
