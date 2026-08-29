from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import ExecutionResult


def _safe_env() -> dict[str, str]:
    allowed = {"SystemRoot", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "PYTHONPATH"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def run_visible_tests(project_dir: Path, timeout_seconds: float = 30) -> ExecutionResult:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    return _run(command, project_dir, "visible_tests", None, timeout_seconds)


def parse_command(command: str | list[str]) -> list[str]:
    if isinstance(command, list):
        return list(command)
    return [part.strip('"') for part in shlex.split(command, posix=False)]


def run_command(
    project_dir: Path,
    command: str | list[str],
    *,
    label: str = "command",
    timeout_seconds: float = 30,
) -> ExecutionResult:
    """Run an explicit project command with stripped credentials and a timeout."""
    return _run(parse_command(command), project_dir, label, None, timeout_seconds)


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        lower = name.lower()
        if name in {".git", ".codex", ".agents", ".venv", "venv", "node_modules", "__pycache__", "evidence", "trajectories"}:
            ignored.add(name)
        elif lower in {".env", ".env.local", ".env.production"} or lower.endswith((".pem", ".key", ".p12", ".pfx")):
            ignored.add(name)
    return ignored


@contextmanager
def isolated_copy(project_dir: Path):
    """Yield a temporary copy that excludes VCS metadata and common secrets."""
    source = project_dir.resolve()
    with tempfile.TemporaryDirectory(prefix="breakfix-sandbox-") as temporary:
        target = Path(temporary) / "project"
        shutil.copytree(source, target, ignore=_copy_ignore)
        yield target


def copy_sanitized_project(project_dir: Path, target: Path) -> Path:
    """Persist a sanitized project snapshot for reproducible later replay."""
    source = project_dir.resolve()
    destination = target.resolve()
    if destination.exists():
        raise FileExistsError(f"snapshot target already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=_copy_ignore)
    return destination


def run_experiment_isolated(
    project_dir: Path,
    experiment_id: str,
    payload: dict[str, Any],
    timeout_seconds: float = 15,
) -> ExecutionResult:
    """Execute the compatible Python project only inside a disposable copy."""
    with isolated_copy(project_dir) as sandbox:
        return run_experiment(sandbox, experiment_id, payload, timeout_seconds)


def run_experiment(
    project_dir: Path,
    experiment_id: str,
    payload: dict[str, Any],
    timeout_seconds: float = 15,
) -> ExecutionResult:
    code = (
        "import json, sys; sys.path.insert(0, '.'); import app; "
        "payload=json.loads(sys.stdin.read()); "
        "result=app.run(payload); "
        "print(json.dumps(result, sort_keys=True))"
    )
    command = [sys.executable, "-I", "-c", code]
    result = _run(command, project_dir, experiment_id, payload, timeout_seconds)
    if result.stdout.strip():
        try:
            result.output = json.loads(result.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            result.output = None
    return result


def _run(
    command: list[str],
    project_dir: Path,
    experiment_id: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
) -> ExecutionResult:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=project_dir,
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            env=_safe_env(),
        )
        exit_code = completed.returncode
        timed_out = False
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        timed_out = True
        stdout = (exc.stdout or "")
        stderr = (exc.stderr or "")
    duration_ms = round((time.perf_counter() - started) * 1000)
    return ExecutionResult(
        experiment_id=experiment_id,
        command=command,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
    )
