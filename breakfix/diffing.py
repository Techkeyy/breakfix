from __future__ import annotations

import difflib
from pathlib import Path


def make_diff(before_path: Path, after_path: Path) -> str:
    before = before_path.read_text(encoding="utf-8").splitlines(keepends=True)
    after = after_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile="before/app.py",
            tofile="after/app.py",
        )
    )
