from __future__ import annotations

import os
import re
import subprocess
import time
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
    resolved_base: str | None = None
    resolved_head: str | None = None


@dataclass(frozen=True)
class ChangeResolution:
    """The exact revisions used for a selected change."""

    change_kind: str
    reference: str | None
    resolved_base: str | None
    resolved_head: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "requested_kind": self.change_kind,
            "requested_reference": self.reference,
            "resolved_base": self.resolved_base,
            "resolved_head": self.resolved_head,
        }


class ChangeResolutionError(RuntimeError):
    """A requested change could not be resolved within the hosted bounds."""

    error_code = "CHANGE_REFERENCE_UNRESOLVED"


HISTORY_DEPTH_STEPS = (16, 64, 256, 1024)
MAX_HISTORY_DEPTH = HISTORY_DEPTH_STEPS[-1]
MAX_HISTORY_ACQUISITION_SECONDS = 180
MAX_GIT_TIMEOUT_SECONDS = 60
MAX_GIT_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_GIT_REPOSITORY_BYTES = 200 * 1024 * 1024


def _safe_env() -> dict[str, str]:
    allowed = {"SystemRoot", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "PYTHONPATH"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def _git(project_root: Path, *args: str, timeout: float | None = None) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={project_root.resolve()}", *args],
        cwd=project_root,
        env=_safe_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if len(result.stdout.encode("utf-8")) > MAX_GIT_OUTPUT_BYTES or len(result.stderr.encode("utf-8")) > MAX_GIT_OUTPUT_BYTES:
        raise RuntimeError("Git command output exceeded the hosted output limit")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise RuntimeError(detail)
    return result.stdout


def _git_fetch(project_root: Path, args: list[str], *, timeout: float) -> bool:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={project_root.resolve()}", "fetch", *args],
        cwd=project_root,
        env=_safe_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if len(result.stdout.encode("utf-8")) > MAX_GIT_OUTPUT_BYTES or len(result.stderr.encode("utf-8")) > MAX_GIT_OUTPUT_BYTES:
        raise RuntimeError("Git fetch output exceeded the hosted output limit")
    return result.returncode == 0


def is_git_repository(project_root: Path, *, timeout: float | None = None) -> bool:
    try:
        _git(project_root, "rev-parse", "--show-toplevel", timeout=timeout)
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


def _revision(
    project_root: Path,
    value: str,
    aliases: dict[str, str] | None = None,
    *,
    timeout: float | None = None,
) -> str:
    target = (aliases or {}).get(value, value)
    return _git(project_root, "rev-parse", "--verify", f"{target}^{{commit}}", timeout=timeout).strip()


def _range_parts(reference: str) -> tuple[str, str]:
    if reference.count("..") != 1 or "..." in reference:
        raise ValueError("a commit range such as BASE..HEAD is required")
    base, head = reference.split("..", 1)
    if not base or not head:
        raise ValueError("a commit range such as BASE..HEAD is required")
    return base, head


def _resolve_change(
    project_root: Path,
    change_kind: str,
    reference: str | None,
    *,
    aliases: dict[str, str] | None = None,
    timeout: float | None = None,
) -> ChangeResolution:
    try:
        if change_kind == "working-tree":
            return ChangeResolution(change_kind, reference, _revision(project_root, "HEAD", aliases, timeout=timeout), None)
        if change_kind == "commit":
            if not reference:
                raise ValueError("a commit reference is required")
            head = _revision(project_root, reference, aliases, timeout=timeout)
            base = _git(project_root, "rev-parse", "--verify", f"{head}^", timeout=timeout).strip()
            return ChangeResolution(change_kind, reference, base, head)
        if change_kind == "range":
            if not reference:
                raise ValueError("a commit range such as BASE..HEAD is required")
            base_ref, head_ref = _range_parts(reference)
            return ChangeResolution(
                change_kind,
                reference,
                _revision(project_root, base_ref, aliases, timeout=timeout),
                _revision(project_root, head_ref, aliases, timeout=timeout),
            )
        if change_kind == "branch":
            if not reference:
                raise ValueError("a base branch or ref is required")
            head = _revision(project_root, "HEAD", aliases, timeout=timeout)
            branch = _revision(project_root, reference, aliases, timeout=timeout)
            base = _git(project_root, "merge-base", branch, head, timeout=timeout).strip()
            return ChangeResolution(change_kind, reference, base, head)
        raise ValueError("change_kind must be working-tree, commit, range, or branch")
    except ValueError:
        raise
    except subprocess.TimeoutExpired:
        raise
    except RuntimeError as exc:
        raise ChangeResolutionError(
            "the requested Git change could not be resolved from the available history"
        ) from exc


def _fetchable_reference(value: str) -> bool:
    if not re.fullmatch(r"[A-Za-z0-9._/@:-]+", value):
        return False
    return not value.startswith((".", "/"))


def _targeted_references(change_kind: str, reference: str | None) -> tuple[str, ...]:
    if not reference:
        return ()
    if change_kind == "commit":
        values = (reference,)
    elif change_kind == "branch":
        values = (reference,)
    elif change_kind == "range":
        values = _range_parts(reference)
    else:
        values = ()
    return tuple(value for value in values if _fetchable_reference(value))


def _repository_size(project_root: Path) -> int:
    total = 0
    for directory, _dirnames, filenames in os.walk(project_root, followlinks=False):
        for name in filenames:
            path = Path(directory) / name
            total += path.stat().st_size
            if total > MAX_GIT_REPOSITORY_BYTES:
                return total
    return total


def ensure_change_history(
    project_root: Path,
    *,
    change_kind: str,
    reference: str | None,
    max_history_depth: int = MAX_HISTORY_DEPTH,
    max_duration_seconds: int = MAX_HISTORY_ACQUISITION_SECONDS,
    fetch_timeout_seconds: int = 45,
    git_timeout_seconds: int = MAX_GIT_TIMEOUT_SECONDS,
    max_repository_bytes: int = MAX_GIT_REPOSITORY_BYTES,
) -> ChangeResolution:
    """Resolve a change, progressively acquiring only bounded shallow history."""
    root = project_root.resolve()
    try:
        return _resolve_change(root, change_kind, reference, timeout=git_timeout_seconds)
    except ChangeResolutionError:
        pass

    depths = tuple(depth for depth in HISTORY_DEPTH_STEPS if depth <= max_history_depth)
    if not depths:
        raise ChangeResolutionError("the requested Git change exceeded the hosted history limit")
    aliases: dict[str, str] = {}
    targeted = _targeted_references(change_kind, reference)
    started = time.monotonic()
    for depth in depths:
        remaining = max_duration_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise ChangeResolutionError("bounded Git history acquisition timed out")
        timeout = max(1.0, min(float(fetch_timeout_seconds), remaining))
        for index, value in enumerate(targeted):
            remaining = max_duration_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise ChangeResolutionError("bounded Git history acquisition timed out")
            timeout = max(1.0, min(float(fetch_timeout_seconds), remaining))
            target = f"refs/breakfix/requested-{index}"
            fetched = _git_fetch(
                root,
                [
                    "--no-tags",
                    "--no-recurse-submodules",
                    "--depth",
                    str(depth),
                    "origin",
                    f"{value}:{target}",
                ],
                timeout=timeout,
            )
            if fetched:
                aliases[value] = target
        # The default fetch deepens the shallow clone's advertised default branch.
        remaining = max_duration_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise ChangeResolutionError("bounded Git history acquisition timed out")
        timeout = max(1.0, min(float(fetch_timeout_seconds), remaining))
        _git_fetch(
            root,
            ["--no-tags", "--no-recurse-submodules", "--depth", str(depth), "origin"],
            timeout=timeout,
        )
        if _repository_size(root) > max_repository_bytes:
            raise ChangeResolutionError("the repository exceeded the hosted size limit while acquiring history")
        try:
            return _resolve_change(root, change_kind, reference, aliases=aliases, timeout=git_timeout_seconds)
        except ChangeResolutionError:
            continue
    raise ChangeResolutionError(
        "the requested Git change could not be resolved within the hosted history limit"
    )


def load_change(
    project_root: Path,
    *,
    task: str | None = None,
    test_command: str | None = None,
    change_kind: str = "working-tree",
    reference: str | None = None,
    ensure_history: bool = False,
    max_history_depth: int = MAX_HISTORY_DEPTH,
    max_history_seconds: int = MAX_HISTORY_ACQUISITION_SECONDS,
    git_timeout_seconds: int | None = None,
    max_repository_bytes: int = MAX_GIT_REPOSITORY_BYTES,
) -> ChangeSnapshot:
    """Read a selected Git change without mutating the developer checkout."""
    root = project_root.resolve()
    if not is_git_repository(root, timeout=git_timeout_seconds):
        raise RuntimeError(f"not a Git repository: {root}")
    if ensure_history:
        resolution = ensure_change_history(
            root,
            change_kind=change_kind,
            reference=reference,
            max_history_depth=max_history_depth,
            max_duration_seconds=max_history_seconds,
            git_timeout_seconds=git_timeout_seconds or MAX_GIT_TIMEOUT_SECONDS,
            max_repository_bytes=max_repository_bytes,
        )
    else:
        resolution = _resolve_change(root, change_kind, reference, timeout=git_timeout_seconds)
    if change_kind == "working-tree":
        diff = _git(root, "diff", "HEAD", "--", timeout=git_timeout_seconds)
    elif change_kind == "commit":
        diff = _git(root, "show", "--format=", "--patch", resolution.resolved_head or "", "--", timeout=git_timeout_seconds)
    elif change_kind == "range":
        diff = _git(root, "diff", f"{resolution.resolved_base}..{resolution.resolved_head}", "--", timeout=git_timeout_seconds)
    elif change_kind == "branch":
        diff = _git(root, "diff", f"{resolution.resolved_base}...{resolution.resolved_head}", "--", timeout=git_timeout_seconds)
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
        resolved_base=resolution.resolved_base,
        resolved_head=resolution.resolved_head,
    )
