from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChangeSnapshot:
    project_root: Path
    change_kind: str
    reference: str | None
    diff: str
    changed_files: tuple[str, ...]
    task: str
    test_command: str


def _safe_env() -> dict[str, str]:
    allowed = {"SystemRoot", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "PYTHONPATH"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={project_root.resolve()}", *args],
        cwd=project_root,
        env=_safe_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise RuntimeError(detail)
    return result.stdout


def is_git_repository(project_root: Path) -> bool:
    try:
        _git(project_root, "rev-parse", "--show-toplevel")
    except RuntimeError:
        return False
    return True


def _changed_files(diff: str) -> tuple[str, ...]:
    files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.add(line[6:])
        elif line.startswith("--- a/"):
            files.add(line[6:])
    return tuple(sorted(files))


def detect_test_command(project_root: Path) -> str:
    if (project_root / "tests").is_dir():
        return "python -m unittest discover -s tests -v"
    if (project_root / "pyproject.toml").is_file() and (project_root / "test").is_dir():
        return "python -m unittest discover -s test -v"
    return "python -m unittest discover -s tests -v"


def load_change(
    project_root: Path,
    *,
    task: str | None = None,
    test_command: str | None = None,
    change_kind: str = "working-tree",
    reference: str | None = None,
) -> ChangeSnapshot:
    """Read a selected Git change without mutating the developer checkout."""
    root = project_root.resolve()
    if not is_git_repository(root):
        raise RuntimeError(f"not a Git repository: {root}")
    if change_kind == "working-tree":
        diff = _git(root, "diff", "HEAD", "--")
    elif change_kind == "commit":
        if not reference:
            raise ValueError("a commit reference is required")
        diff = _git(root, "show", "--format=", "--patch", reference, "--")
    elif change_kind == "range":
        if not reference or ".." not in reference:
            raise ValueError("a commit range such as BASE..HEAD is required")
        diff = _git(root, "diff", reference, "--")
    elif change_kind == "branch":
        if not reference:
            raise ValueError("a base branch or ref is required")
        diff = _git(root, "diff", f"{reference}...HEAD", "--")
    else:
        raise ValueError("change_kind must be working-tree, commit, range, or branch")
    return ChangeSnapshot(
        project_root=root,
        change_kind=change_kind,
        reference=reference,
        diff=diff,
        changed_files=_changed_files(diff),
        task=task or "Analyze the selected change for behavior regressions.",
        test_command=test_command or detect_test_command(root),
    )
