from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .models import ExecutionResult


def _safe_env() -> dict[str, str]:
    allowed = {"SystemRoot", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "PYTHONPATH"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def run_visible_tests(project_dir: Path, timeout_seconds: float = 30) -> ExecutionResult:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    return _run(command, project_dir, "visible_tests", None, timeout_seconds)


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
