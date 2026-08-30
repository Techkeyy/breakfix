"""Small hosted HTTP facade around the existing BreakFix engine."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .evidence import write_json
from .git_project import load_change


MAX_REQUEST_BYTES = 64 * 1024
MAX_REPOSITORY_BYTES = 200 * 1024 * 1024
MAX_CLONE_SECONDS = 180
MAX_HISTORY_SECONDS = 180
MAX_HISTORY_DEPTH = 1024
MAX_JOB_SECONDS = 15 * 60
MAX_TEXT_BYTES = 20_000
SUPPORTED_HOSTS = {"github.com", "www.github.com", "gitlab.com", "www.gitlab.com", "bitbucket.org"}
CANONICAL_REPOSITORY = "https://github.com/Techkeyy/breakfix"
REFERENCE_RE = re.compile(r"^[A-Za-z0-9._/@^~:-]+$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _short_text(value: Any, limit: int = MAX_TEXT_BYTES) -> str:
    text = str(value or "")
    return text[:limit]


def _public_value(value: Any, *, depth: int = 0) -> Any:
    """Keep the public evidence projection bounded and JSON-only."""
    if depth >= 4:
        return "[truncated]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _short_text(value, MAX_TEXT_BYTES)
    if isinstance(value, list):
        return [_public_value(item, depth=depth + 1) for item in value[:64]]
    if isinstance(value, dict):
        return {
            str(key)[:200]: _public_value(item, depth=depth + 1)
            for key, item in list(value.items())[:64]
        }
    return _short_text(value)


def normalize_repository_url(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("repository_url must be a valid HTTPS Git repository URL")
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname not in SUPPORTED_HOSTS:
        raise ValueError("only HTTPS repositories from supported public hosts are accepted")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("repository_url must not contain credentials, query parameters, or fragments")
    path = parsed.path.rstrip("/")
    if not path or path == "/" or ".." in path.split("/"):
        raise ValueError("repository_url must identify a repository path")
    return f"https://{parsed.hostname}{path}"


def _is_canonical_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.hostname == "github.com" and parsed.path.rstrip("/").removesuffix(".git").lower() == "/techkeyy/breakfix"


def validate_job_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    repository_url = normalize_repository_url(payload.get("repository_url"))
    demo_value = payload.get("demo", False)
    if not isinstance(demo_value, bool):
        raise ValueError("demo must be a boolean")
    demo = demo_value
    if demo and not _is_canonical_url(repository_url):
        raise ValueError("the canonical demo requires the public Techkeyy/breakfix repository")
    task = payload.get("task")
    if task is not None and (not isinstance(task, str) or len(task) > 2_000):
        raise ValueError("task must be at most 2,000 characters")
    request: dict[str, Any] = {
        "repository_url": repository_url,
        "demo": demo,
        "task": task,
    }
    if not demo:
        change = payload.get("change")
        if not isinstance(change, dict):
            raise ValueError("change.kind and change.reference are required for non-demo jobs")
        kind = change.get("kind", "commit")
        reference = change.get("reference")
        if kind not in {"commit", "branch", "range"} or not isinstance(reference, str) or not REFERENCE_RE.fullmatch(reference) or len(reference) > 200:
            raise ValueError("change must contain a supported kind and safe Git reference")
        request["change"] = {"kind": kind, "reference": reference}
        test_command = payload.get("test_command")
        if test_command is not None and (not isinstance(test_command, str) or not test_command.strip() or len(test_command) > 300):
            raise ValueError("test_command must be at most 300 characters")
        request["test_command"] = test_command
    return request


def _safe_env() -> dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "GIT_TERMINAL_PROMPT"}
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _bounded_run(command: list[str], *, cwd: Path | None = None, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=_safe_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _reject_symlinks(root: Path) -> None:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        for name in [*dirnames, *filenames]:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError("repositories containing symlinks are not accepted by hosted mode")


def _tree_size(root: Path) -> int:
    total = 0
    for directory, _dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            path = Path(directory) / name
            total += path.stat().st_size
            if total > MAX_REPOSITORY_BYTES:
                return total
    return total


def _public_experiment(record: dict[str, Any]) -> dict[str, Any]:
    actual = record.get("actual_behavior") or {}
    return {
        "experiment_id": record.get("experiment_id"),
        "description": _short_text(record.get("description"), 2_000),
        "assumption": record.get("assumption"),
        "expected_behavior": _short_text(record.get("expected_behavior"), 2_000),
        "actual_behavior": {
            "process_failed": bool(actual.get("process_failed")),
            "output": _public_value(actual.get("output")),
        },
        "evidence_state": record.get("evidence_state"),
    }


def _result_status(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "exit_code": value.get("exit_code"),
        "timed_out": bool(value.get("timed_out")),
        "process_failed": bool(value.get("process_failed")),
        "duration_ms": value.get("duration_ms"),
    }


def public_evidence(evidence: Path, job_id: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return an allowlisted evidence projection with no server paths or raw logs."""
    analysis_path = evidence / "analysis.json"
    analysis: dict[str, Any] = {}
    if analysis_path.is_file():
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            analysis = {}
    planner: dict[str, Any] = {}
    planner_path = evidence / "planner.json"
    if planner_path.is_file():
        try:
            planner = json.loads(planner_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            planner = {}
    telemetry: dict[str, Any] = {}
    telemetry_path = evidence / "provider-telemetry.json"
    if telemetry_path.is_file():
        try:
            telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            telemetry = {}
    records = analysis.get("experiment_records") or []
    public: dict[str, Any] = {
        "job_id": job_id,
        "status": (state or {}).get("status", "COMPLETED"),
        "outcome": analysis.get("outcome"),
        "provider_status": analysis.get("provider_status"),
        "task": analysis.get("task"),
        "changed_files": analysis.get("changed_files", []),
        "change_resolution": analysis.get("change_resolution"),
        "selected_experiments": analysis.get("selected_experiments", []),
        "experiments_run": analysis.get("experiments_run", 0),
        "regression": analysis.get("regression"),
        "assumptions": planner.get("assumptions", []),
        "unsupported_assumptions": planner.get("unsupported_assumptions", []),
        "experiments": [_public_experiment(item) for item in records if isinstance(item, dict)],
        "visible_tests": _result_status(evidence / "visible-tests" / "result.json"),
        "telemetry": telemetry,
    }
    proposal_path = evidence / "fix" / "proposal.json"
    if proposal_path.is_file():
        try:
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            proposal = {}
        value = proposal.get("proposal") if isinstance(proposal.get("proposal"), dict) else {}
        public["fix"] = {
            "status": proposal.get("status"),
            "human_approval_required": bool(proposal.get("human_approval_required")),
            "summary": _short_text(value.get("summary"), 4_000),
            "patch": _short_text(value.get("patch"), 30_000),
            "files_changed": value.get("files_changed", []),
            "tests_to_run": value.get("tests_to_run", []),
        }
    verification_path = evidence / "fix" / "verification.json"
    if verification_path.is_file():
        try:
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            verification = {}
        public["verification"] = {
            "status": verification.get("status"),
            "experiment_process_failed": bool((verification.get("experiment") or {}).get("process_failed")),
            "visible_tests": _result_status_from_value(verification.get("visible_tests")),
            "regression": _result_status_from_value(verification.get("regression")),
        }
    decision_path = evidence / "fix" / "decision.json"
    if decision_path.is_file():
        try:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            decision = {}
        public["fix_decision"] = {"status": decision.get("status")}
    return public


def _result_status_from_value(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "exit_code": value.get("exit_code"),
        "timed_out": bool(value.get("timed_out")),
        "process_failed": bool(value.get("process_failed")),
        "duration_ms": value.get("duration_ms"),
    }


class JobManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.jobs_root = self.root / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self.image = os.environ.get("BREAKFIX_ENGINE_IMAGE", "breakfix-engine:latest")
        self.provider_env_file = Path(os.environ.get("BREAKFIX_PROVIDER_ENV_FILE", "/etc/breakfix/breakfix.env"))
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="breakfix-job")
        self.lock = threading.RLock()
        self.active: set[str] = set()

    def _directory(self, job_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9-]{36}", job_id):
            raise KeyError("job not found")
        return self.jobs_root / job_id

    def _read(self, job_id: str) -> dict[str, Any]:
        directory = self._directory(job_id)
        path = directory / "job.json"
        if not path.is_file():
            raise KeyError("job not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, job_id: str, **updates: Any) -> dict[str, Any]:
        with self.lock:
            current = self._read(job_id)
            current.update(updates, updated_at=_now())
            write_json(self._directory(job_id) / "job.json", current)
            return current

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            if len(self.active) >= 1:
                raise RuntimeError("job capacity is temporarily full; retry shortly")
            job_id = str(uuid.uuid4())
            directory = self._directory(job_id)
            (directory / "evidence").mkdir(parents=True)
            record = {
                "job_id": job_id,
                "status": "QUEUED",
                "operation": "analyze",
                "created_at": _now(),
                "updated_at": _now(),
                "repository_url": request["repository_url"],
                "demo": request["demo"],
            }
            write_json(directory / "job.json", record)
            self.active.add(job_id)
            self.executor.submit(self._run_analysis, job_id, request)
            return record

    def submit_operation(self, job_id: str, operation: str) -> dict[str, Any]:
        with self.lock:
            if len(self.active) >= 1:
                raise RuntimeError("job capacity is temporarily full; retry shortly")
            record = self._read(job_id)
            if record.get("status") in {"QUEUED", "RUNNING", "PROPOSAL_RUNNING", "APPLYING", "VERIFYING"}:
                raise RuntimeError("job already has an active operation")
            if operation == "propose-fix" and record.get("outcome") != "CONFIRMED BREAK":
                raise RuntimeError("a confirmed break is required before proposing a fix")
            if operation == "approve-fix":
                proposal = self._directory(job_id) / "evidence" / "fix" / "proposal.json"
                if not proposal.is_file():
                    raise RuntimeError("no fix proposal is available for approval")
            if operation == "verify" and not (self._directory(job_id) / "evidence" / "approved_snapshot").is_dir():
                raise RuntimeError("an approved fix is required before verification")
            status = {"propose-fix": "PROPOSAL_RUNNING", "approve-fix": "APPLYING", "reject-fix": "REJECTED", "verify": "VERIFYING"}[operation]
            record = self._write(job_id, status=status, operation=operation, error_code=None, error=None)
            if operation == "reject-fix":
                write_json(self._directory(job_id) / "evidence" / "fix" / "decision.json", {"status": "REJECTED", "decided_at": _now()})
                return self._write(job_id, status="REJECTED", operation=operation)
            self.active.add(job_id)
            self.executor.submit(self._run_operation, job_id, operation)
            return record

    def get(self, job_id: str) -> dict[str, Any]:
        record = self._read(job_id)
        evidence = self._directory(job_id) / "evidence"
        if (evidence / "analysis.json").is_file() or (evidence / "fix" / "proposal.json").is_file() or (evidence / "fix" / "verification.json").is_file():
            record["result"] = public_evidence(evidence, job_id, record)
        return record

    def evidence(self, job_id: str) -> dict[str, Any]:
        record = self._read(job_id)
        return public_evidence(self._directory(job_id) / "evidence", job_id, record)

    def _clone(self, job_id: str, request: dict[str, Any]) -> Path:
        directory = self._directory(job_id)
        project = directory / "project"
        result = _bounded_run(
            ["git", "-c", "core.hooksPath=/dev/null", "clone", "--depth", "1", "--no-tags", "--no-recurse-submodules", request["repository_url"], str(project)],
            cwd=directory,
            timeout=MAX_CLONE_SECONDS,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise RuntimeError("PRIVATE_OR_INACCESSIBLE_REPOSITORY: " + _short_text(detail, 500))
        _reject_symlinks(project)
        if _tree_size(project) > MAX_REPOSITORY_BYTES:
            raise RuntimeError("REPOSITORY_TOO_LARGE")
        return project

    def _docker(self, job_id: str, mode: str, *, project: Path | None = None, request: Path | None = None) -> None:
        directory = self._directory(job_id)
        evidence = directory / "evidence"
        command = [
            "docker", "run", "--rm", "--name", f"breakfix-job-{job_id[:12]}",
            "--cpus", "1.0", "--memory", "768m", "--pids-limit", "128", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=128m",
            "--tmpfs", "/run:rw,nosuid,nodev,noexec,size=16m",
            "--network", "bridge",
            "--env-file", str(self.provider_env_file),
        ]
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            command.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
        if project is not None:
            command.extend(["--mount", f"type=bind,src={project},dst=/job/project,readonly"])
        command.extend(["--mount", f"type=bind,src={evidence},dst=/job/evidence"])
        if request is not None:
            command.extend(["--mount", f"type=bind,src={request},dst=/job/request.json,readonly"])
        command.extend([self.image, "python", "-m", "breakfix.remote_worker", "--mode", mode, "--evidence", "/job/evidence"])
        if project is not None:
            command.extend(["--project", "/job/project"])
        if request is not None:
            command.extend(["--request", "/job/request.json"])
        result = _bounded_run(command, cwd=directory, timeout=MAX_JOB_SECONDS)
        worker_result = evidence / "worker-result.json"
        if result.returncode != 0 and not worker_result.is_file():
            raise RuntimeError("CONTAINER_FAILURE: " + _short_text(result.stderr or result.stdout, 800))
        if worker_result.is_file():
            payload = json.loads(worker_result.read_text(encoding="utf-8"))
            if not payload.get("ok"):
                raise RuntimeError(f"{payload.get('error_code', 'WORKER_ERROR')}: {_short_text(payload.get('error'), 800)}")

    def _run_analysis(self, job_id: str, request: dict[str, Any]) -> None:
        directory = self._directory(job_id)
        try:
            self._write(job_id, status="RUNNING", operation="analyze")
            request_path = directory / "request.json"
            project = self._clone(job_id, request)
            change = request.get("change") or {}
            if change:
                snapshot = load_change(
                    project,
                    task=request.get("task"),
                    test_command=request.get("test_command"),
                    change_kind=change.get("kind", "commit"),
                    reference=change.get("reference"),
                    ensure_history=True,
                    max_history_depth=MAX_HISTORY_DEPTH,
                    max_history_seconds=MAX_HISTORY_SECONDS,
                    max_repository_bytes=MAX_REPOSITORY_BYTES,
                )
                request["resolved_change"] = {
                    "requested_kind": snapshot.change_kind,
                    "requested_reference": snapshot.reference,
                    "resolved_base": snapshot.resolved_base,
                    "resolved_head": snapshot.resolved_head,
                }
            write_json(request_path, request)
            self._docker(job_id, "analyze", project=project, request=request_path)
            analysis_path = directory / "evidence" / "analysis.json"
            if not analysis_path.is_file():
                raise RuntimeError("CONTAINER_FAILURE: analysis result is missing")
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            self._write(job_id, status="COMPLETED", operation="analyze", outcome=analysis.get("outcome"), provider_status=analysis.get("provider_status"), experiments_run=analysis.get("experiments_run", 0))
        except subprocess.TimeoutExpired:
            self._write(job_id, status="FAILED", error_code="TIMEOUT", error="the bounded hosted job timed out")
        except Exception as exc:
            error_code = getattr(exc, "error_code", type(exc).__name__)
            self._write(job_id, status="FAILED", error_code=error_code, error=_short_text(exc, 1_000))
        finally:
            project = directory / "project"
            if project.exists():
                shutil.rmtree(project, ignore_errors=True)
            request_path = directory / "request.json"
            request_path.unlink(missing_ok=True)
            with self.lock:
                self.active.discard(job_id)

    def _run_operation(self, job_id: str, operation: str) -> None:
        try:
            mode = {"propose-fix": "propose-fix", "approve-fix": "apply-fix", "verify": "verify-fix"}[operation]
            self._docker(job_id, mode)
            evidence = self._directory(job_id) / "evidence"
            if operation == "propose-fix":
                proposal = json.loads((evidence / "fix" / "proposal.json").read_text(encoding="utf-8"))
                self._write(job_id, status="COMPLETED", operation=operation, outcome=self._read(job_id).get("outcome"), proposal_status=proposal.get("status"))
            elif operation == "approve-fix":
                self._write(job_id, status="APPROVED", operation=operation, approval_status="APPROVED")
            else:
                verification = json.loads((evidence / "fix" / "verification.json").read_text(encoding="utf-8"))
                self._write(job_id, status="COMPLETED", operation=operation, verification_status=verification.get("status"))
        except subprocess.TimeoutExpired:
            self._write(job_id, status="FAILED", error_code="TIMEOUT", error="the bounded hosted operation timed out")
        except Exception as exc:
            self._write(job_id, status="FAILED", error_code=type(exc).__name__, error=_short_text(exc, 1_000))
        finally:
            with self.lock:
                self.active.discard(job_id)


class APIHandler(BaseHTTPRequestHandler):
    manager: JobManager
    allowed_origins: set[str]

    def _origin(self) -> str | None:
        value = self.headers.get("Origin")
        return value if value in self.allowed_origins else None

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > MAX_REQUEST_BYTES:
            raise ValueError("request body is missing or exceeds the hosted request limit")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/health":
                self._send(200, {"status": "ok", "service": "breakfix-api"})
                return
            match = re.fullmatch(r"/api/jobs/([a-f0-9-]{36})(/evidence)?", parsed.path)
            if not match:
                self._send(404, {"error_code": "NOT_FOUND", "error": "route not found"})
                return
            job_id = match.group(1)
            self._send(200, self.manager.evidence(job_id) if match.group(2) else self.manager.get(job_id))
        except KeyError:
            self._send(404, {"error_code": "JOB_NOT_FOUND", "error": "job not found"})
        except Exception as exc:
            self._send(500, {"error_code": type(exc).__name__, "error": _short_text(exc, 1_000)})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/jobs":
                request = validate_job_request(self._read_json())
                record = self.manager.create(request)
                self._send(202, record)
                return
            match = re.fullmatch(r"/api/jobs/([a-f0-9-]{36})/(propose-fix|approve-fix|reject-fix|verify)", parsed.path)
            if not match:
                self._send(404, {"error_code": "NOT_FOUND", "error": "route not found"})
                return
            if self.headers.get("Content-Length", "0") not in {"", "0"}:
                self._read_json()
            record = self.manager.submit_operation(match.group(1), match.group(2))
            self._send(202, record)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error_code": "INVALID_REQUEST", "error": _short_text(exc, 1_000)})
        except KeyError:
            self._send(404, {"error_code": "JOB_NOT_FOUND", "error": "job not found"})
        except RuntimeError as exc:
            self._send(409, {"error_code": "JOB_REJECTED", "error": _short_text(exc, 1_000)})
        except Exception as exc:
            self._send(500, {"error_code": type(exc).__name__, "error": _short_text(exc, 1_000)})

    def log_message(self, *_args: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8788, data_dir: Path | None = None) -> None:
    root = data_dir or Path(os.environ.get("BREAKFIX_DATA_DIR", "./.breakfix-data"))
    origins = {item.strip() for item in os.environ.get("BREAKFIX_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if item.strip()}
    manager = JobManager(root)
    handler = type("ConfiguredAPIHandler", (APIHandler,), {"manager": manager, "allowed_origins": origins})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"BreakFix API listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
