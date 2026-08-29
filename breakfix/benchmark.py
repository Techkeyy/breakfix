from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cases(root: Path) -> list[dict[str, Any]]:
    cases_root = root / "benchmark" / "cases"
    cases = []
    for path in sorted(cases_root.glob("*/public.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


def load_ground_truth(root: Path) -> dict[str, Any]:
    path = root / "benchmark" / "ground_truth.json"
    return json.loads(path.read_text(encoding="utf-8"))


def case_dir(root: Path, case_id: str) -> Path:
    return root / "benchmark" / "cases" / case_id


def after_dir(root: Path, case_id: str) -> Path:
    return case_dir(root, case_id) / "after"


def before_dir(root: Path, case_id: str) -> Path:
    return case_dir(root, case_id) / "before"

