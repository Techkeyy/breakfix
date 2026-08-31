from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "breakfix-post-hardening-evaluation-v1"
EXPECTED_CASE_COUNT = 16
EXPECTED_MATRIX_EXPERIMENTS = 8
PRODUCT_MAX_EXPERIMENTS = 3
EXACT_LIVE_CALLS = 32
GENERIC_PROMPT_ID = "final-generic-comparator-v1"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_git_head() -> str | None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={PROJECT_ROOT}", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _git_status() -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={PROJECT_ROOT}", "status", "--short"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip()


def _aggregate_telemetry(items: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = (
        "model_calls",
        "successful_provider_responses",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "monetary_cost_usd",
        "latency_ms",
        "retries",
    )
    result: dict[str, Any] = {key: 0 for key in numeric}
    result["finish_reasons"] = []
    result["response_formats"] = []
    result["reasoning_content_present"] = False
    for item in items:
        for key in numeric:
            value = item.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                result[key] += value
        result["finish_reasons"].extend(item.get("finish_reasons") or [])
        result["response_formats"].extend(item.get("response_formats") or [])
        result["reasoning_content_present"] = result["reasoning_content_present"] or bool(
            item.get("reasoning_content_present")
        )
    result["response_formats"] = sorted(set(result["response_formats"]))
    return result


def _holdout_manifest_hash(public_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in public_root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(public_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _copy_history_free_workspace(target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=False)
    def ignore_history(_directory: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name == "__pycache__" or name in {"phase1.py", "phase15.py", "phase2a.py", "phase2b.py"}
        }

    shutil.copytree(PROJECT_ROOT / "breakfix", target / "breakfix", ignore=ignore_history)
    shutil.copytree(
        PROJECT_ROOT / "benchmark" / "post_hardening_holdout",
        target / "benchmark" / "post_hardening_holdout",
    )
    for name in ("pyproject.toml", ".env.example"):
        source = PROJECT_ROOT / name
        if source.exists():
            shutil.copy2(source, target / name)
    if (target / ".git").exists():
        raise RuntimeError("history-free workspace unexpectedly contains .git")
    return target


def _public_case_files(case_root: Path) -> list[Path]:
    return sorted(path for path in case_root.rglob("*") if path.is_file())


def _leakage_audit(public_root: Path, oracle: dict[str, Any]) -> dict[str, Any]:
    cases = oracle.get("cases") if isinstance(oracle, dict) else None
    if not isinstance(cases, dict):
        return {"passed": False, "reason": "oracle cases object missing"}
    case_dirs = sorted(path for path in public_root.iterdir() if path.is_dir())
    forbidden_terms = (
        "expected_outputs",
        "oracle",
        "fault_experiments",
        "seeded_fault",
        "safe_case",
        "unsafe_case",
        "ground_truth",
        "expected_verdict",
    )
    term_hits: list[str] = []
    truth_term_hits: list[str] = []
    answer_bearing_paths: list[str] = []
    overlap_hits: list[str] = []
    old_hashes: dict[str, str] = {}
    for path in PROJECT_ROOT.glob("benchmark/**"):
        if not path.is_file() or "post_hardening_holdout" in path.parts:
            continue
        old_hashes.setdefault(_sha256(path), str(path.relative_to(PROJECT_ROOT)))
    allowed_names = {"public.json", "app.py", "test_app.py"}
    for case_root in case_dirs:
        for path in _public_case_files(case_root):
            relative = path.relative_to(public_root).as_posix()
            if path.name not in allowed_names:
                answer_bearing_paths.append(relative)
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            for term in forbidden_terms:
                if term in lower:
                    term_hits.append(f"{relative}:{term}")
            if re.search(r"\b(?:truth|fault|verdict)\b", lower):
                truth_term_hits.append(relative)
            file_hash = _sha256(path)
            if file_hash in old_hashes:
                overlap_hits.append(f"{relative}={old_hashes[file_hash]}")
    public_ids = {path.name for path in case_dirs}
    oracle_ids = set(cases)
    required_files_ok = all(
        all((case_root / relative).is_file() for relative in ("public.json", "before/app.py", "after/app.py", "after/tests/test_app.py"))
        for case_root in case_dirs
    )
    manifest_path = public_root / "manifest.json"
    manifest_ok = manifest_path.is_file()
    return {
        "public_case_count": len(case_dirs),
        "oracle_case_count": len(oracle_ids),
        "case_id_sets_match": public_ids == oracle_ids,
        "required_case_files_present": required_files_ok,
        "manifest_present": manifest_ok,
        "forbidden_term_hits": sorted(set(term_hits)),
        "truth_term_hits": sorted(set(truth_term_hits)),
        "answer_bearing_paths": sorted(set(answer_bearing_paths)),
        "exact_overlap_hits": sorted(set(overlap_hits)),
        "passed": (
            len(case_dirs) == EXPECTED_CASE_COUNT
            and len(oracle_ids) == EXPECTED_CASE_COUNT
            and public_ids == oracle_ids
            and required_files_ok
            and manifest_ok
            and not term_hits
            and not truth_term_hits
            and not answer_bearing_paths
            and not overlap_hits
        ),
    }


def _workspace_audit(workspace: Path, truth_path: Path) -> dict[str, Any]:
    forbidden_roots = (".git", "final_holdout", "phase1", "phase2", "evidence", "trajectories")
    forbidden_files: list[str] = []
    truth_like_files: list[str] = []
    for path in workspace.rglob("*"):
        relative = path.relative_to(workspace).as_posix().lower()
        if any(part in relative.split("/") for part in forbidden_roots):
            forbidden_files.append(relative)
        if path.is_file():
            lower = path.read_text(encoding="utf-8", errors="replace").lower()
            if any(term in lower for term in ("expected_outputs", "seeded_fault_id", "deterministic_scoring_notes")):
                truth_like_files.append(relative)
    oracle_not_visible = not any(path.name == truth_path.name for path in workspace.rglob("*"))
    return {
        "git_absent": not (workspace / ".git").exists(),
        "old_evidence_or_holdout_paths_absent": not forbidden_files,
        "truth_like_files_absent": not truth_like_files,
        "oracle_filename_absent": oracle_not_visible,
        "forbidden_paths": sorted(set(forbidden_files)),
        "truth_like_files": sorted(set(truth_like_files)),
        "passed": not forbidden_files and not truth_like_files and oracle_not_visible,
    }


def _execution_complete(result: dict[str, Any]) -> bool:
    return all(
        key in result
        for key in ("command", "stdout", "stderr", "exit_code", "timed_out", "duration_ms", "process_failed")
    )


def _oracle_outcome(execution: dict[str, Any], expected_outputs: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    if experiment_id not in expected_outputs:
        return {
            "state": "UNSUPPORTED",
            "evidence_complete": _execution_complete(execution),
            "matches_expected": None,
            "oracle_available": False,
        }
    complete = _execution_complete(execution)
    if not complete:
        return {"state": "ERROR", "evidence_complete": False, "matches_expected": None, "oracle_available": True}
    matches = not bool(execution.get("process_failed")) and execution.get("output") == expected_outputs[experiment_id]
    return {
        "state": "NO BREAK CONFIRMED" if matches else "CONFIRMED BREAK",
        "evidence_complete": True,
        "matches_expected": matches,
        "oracle_available": True,
    }


def _diff_for_case(case_root: Path) -> str:
    before = (case_root / "before" / "app.py").read_text(encoding="utf-8", errors="replace").splitlines(True)
    after = (case_root / "after" / "app.py").read_text(encoding="utf-8", errors="replace").splitlines(True)
    return "".join(difflib.unified_diff(before, after, fromfile="a/app.py", tofile="b/app.py"))


def _copy_public_product_evidence(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("evaluation.json", "oracle.json", "truth.json"),
    )


def _baseline_telemetry(result: Any, case_id: str) -> dict[str, Any]:
    responses = [attempt.response for attempt in result.attempts if attempt.response]
    return {
        "case_id": case_id,
        "model_calls": len(result.attempts),
        "successful_provider_responses": len(responses),
        "input_tokens": sum((response.input_tokens or 0) for response in responses),
        "output_tokens": sum((response.output_tokens or 0) for response in responses),
        "total_tokens": sum((response.total_tokens or 0) for response in responses),
        "monetary_cost_usd": sum((response.monetary_cost_usd or 0) for response in responses),
        "latency_ms": sum(response.latency_ms for response in responses),
        "retries": sum(response.retries for response in responses),
        "finish_reasons": [response.finish_reason for response in responses],
        "response_formats": [response.response_format for response in responses if response.response_format],
        "reasoning_content_present": any(bool(response.reasoning_text) for response in responses),
    }


def _score_case_lane(case_results: list[dict[str, Any]], oracle_cases: dict[str, dict[str, Any]], *, lane: str) -> dict[str, Any]:
    confirmed_faults = 0
    false_confirmed_breaks = 0
    errors = 0
    unsupported = 0
    for result in case_results:
        case_truth = oracle_cases[result["case_id"]]
        state = result.get("state")
        if state == "ERROR":
            errors += 1
        if state == "UNSUPPORTED":
            unsupported += 1
        if state == "CONFIRMED BREAK":
            if case_truth["faulty"]:
                confirmed_faults += 1
            else:
                false_confirmed_breaks += 1
    fault_count = sum(1 for item in oracle_cases.values() if item["faulty"])
    safe_count = len(oracle_cases) - fault_count
    recall = confirmed_faults / fault_count if fault_count else None
    false_rate = false_confirmed_breaks / safe_count if safe_count else None
    eligible = confirmed_faults == fault_count and false_confirmed_breaks == 0 and errors == 0
    return {
        "lane": lane,
        "fault_cases": fault_count,
        "safe_cases": safe_count,
        "confirmed_fault_cases": confirmed_faults,
        "seeded_fault_recall": recall,
        "false_confirmed_breaks": false_confirmed_breaks,
        "false_confirmed_break_rate": false_rate,
        "error_cases": errors,
        "unsupported_cases": unsupported,
        "eligible": eligible,
    }


class BudgetedProvider:
    """Evaluator-only adapter enforcing the frozen global completion ceiling."""

    def __init__(self, inner: Any, maximum: int) -> None:
        self.inner = inner
        self.maximum = maximum
        self.calls = 0
        self.context_lane = "unknown"
        self.context_case = "unknown"
        self.call_log: list[dict[str, Any]] = []

    def complete_structured(
        self,
        prompt: str,
        *,
        validator: Callable[[str], dict[str, Any]] | None = None,
        max_recovery_attempts: int = 1,
    ) -> Any:
        from breakfix.provider import ProviderError, bounded_structured_recovery

        def complete(request_prompt: str) -> Any:
            if self.calls >= self.maximum:
                raise ProviderError("frozen live completion budget exhausted before another provider call")
            self.calls += 1
            entry: dict[str, Any] = {
                "call_number": self.calls,
                "lane": self.context_lane,
                "case_id": self.context_case,
                "prompt_sha256": _sha256_bytes(request_prompt.encode("utf-8")),
                "started_at_utc": _utc_now(),
            }
            try:
                response = self.inner.complete(request_prompt, response_format={"type": "json_object"})
            except ProviderError as exc:
                entry.update({"status": "PROVIDER_ERROR", "error": str(exc), "completed_at_utc": _utc_now()})
                self.call_log.append(entry)
                raise
            entry.update(
                {
                    "status": "RESPONSE",
                    "provider": response.provider,
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                    "retries": response.retries,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "completed_at_utc": _utc_now(),
                }
            )
            self.call_log.append(entry)
            return response

        return bounded_structured_recovery(
            complete,
            prompt,
            validator=validator,
            max_recovery_attempts=max_recovery_attempts,
        )


def _validate_oracle_shape(oracle: dict[str, Any]) -> None:
    cases = oracle.get("cases")
    if not isinstance(cases, dict) or len(cases) != EXPECTED_CASE_COUNT:
        raise SystemExit("external oracle must contain exactly 16 cases")
    if sum(1 for item in cases.values() if item.get("faulty") is True) != 8:
        raise SystemExit("external oracle must contain exactly 8 faulty cases")
    if sum(1 for item in cases.values() if item.get("faulty") is False) != 8:
        raise SystemExit("external oracle must contain exactly 8 safe cases")
    required = {"faulty", "seeded_fault_id", "expected_surface", "expected_predicate", "expected_outputs", "deterministic_scoring_notes"}
    for case_id, item in cases.items():
        if not isinstance(item, dict) or set(item) != required:
            raise SystemExit(f"oracle fields are not frozen for case {case_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen post-hardening independent evaluation.")
    parser.add_argument("--oracle-path", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument("--public-evidence-root", type=Path, default=PROJECT_ROOT / "evidence")
    args = parser.parse_args()

    oracle_path = args.oracle_path.resolve()
    if not oracle_path.is_file():
        raise SystemExit(f"oracle file not found: {oracle_path}")
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    if not isinstance(oracle, dict):
        raise SystemExit("oracle file must contain an object")
    _validate_oracle_shape(oracle)
    oracle_cases = oracle["cases"]

    run_id = "post-hardening-eval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_root = (args.raw_root.resolve() if args.raw_root else Path(tempfile.gettempdir()) / run_id).resolve()
    if raw_root.exists():
        raise SystemExit(f"refusing to overwrite raw root: {raw_root}")
    raw_root.mkdir(parents=True)
    workspace = _copy_history_free_workspace(raw_root / "workspace")
    public_root = workspace / "benchmark" / "post_hardening_holdout"
    public_evidence = args.public_evidence_root.resolve() / run_id
    public_evidence.mkdir(parents=True, exist_ok=False)
    if str(oracle_path).startswith(str(workspace)) or str(oracle_path).startswith(str(public_evidence)):
        raise SystemExit("oracle must remain outside evaluation and published evidence roots")

    leakage = _leakage_audit(public_root, oracle)
    workspace_audit = _workspace_audit(workspace, oracle_path)
    _write_json(raw_root / "leakage-audit.json", {"public_holdout": leakage, "history_free_workspace": workspace_audit})
    if not leakage["passed"] or not workspace_audit["passed"]:
        raise SystemExit("pre-execution leakage audit failed")

    manifest = json.loads((public_root / "manifest.json").read_text(encoding="utf-8"))
    case_dirs = sorted(path for path in public_root.iterdir() if path.is_dir())
    if len(case_dirs) != EXPECTED_CASE_COUNT or manifest.get("case_ids") != [path.name for path in case_dirs]:
        raise SystemExit("holdout manifest does not match the sealed case set")

    sys.path.insert(0, str(workspace))
    from breakfix.agent_contract import validate_phase2b_baseline_response
    from breakfix.experiments import EXPERIMENTS, BASE_CONTEXT, payload_for
    from breakfix.final_eval_prompts import render_final_generic_prompt
    from breakfix.git_project import ChangeSnapshot
    from breakfix.product import analyze_change
    from breakfix.provider import DirectProvider
    from breakfix.executor import run_command, run_experiment_isolated

    visible_results: list[dict[str, Any]] = []
    for case_root in case_dirs:
        visible = run_command(case_root / "after", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], label="visible_tests", timeout_seconds=45)
        item = {"case_id": case_root.name, **visible.as_dict()}
        visible_results.append(item)
        _write_json(raw_root / "preflight" / "visible-tests" / case_root.name / "result.json", item)
        _write_text(raw_root / "preflight" / "visible-tests" / case_root.name / "stdout.log", visible.stdout)
        _write_text(raw_root / "preflight" / "visible-tests" / case_root.name / "stderr.log", visible.stderr)
    if any(item.get("exit_code") != 0 or item.get("process_failed") or item.get("timed_out") for item in visible_results):
        raise SystemExit("one or more fresh holdout visible test suites failed")

    current_tests = run_command(PROJECT_ROOT, [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], label="current_unit_tests", timeout_seconds=180)
    _write_json(raw_root / "preflight" / "current-unit-tests.json", current_tests.as_dict())
    _write_text(raw_root / "preflight" / "current-unit-tests.stdout.log", current_tests.stdout)
    _write_text(raw_root / "preflight" / "current-unit-tests.stderr.log", current_tests.stderr)
    if current_tests.exit_code != 0 or current_tests.process_failed or current_tests.timed_out:
        raise SystemExit("current BreakFix unit tests failed before provider calls")

    provider = DirectProvider()
    credential_present = bool(os.environ.get("BREAKFIX_DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))
    if (
        provider.provider != "deepseek"
        or provider.model != "deepseek-v4-pro"
        or provider.reasoning_effort != "high"
        or provider.max_output_tokens != 12000
        or not credential_present
    ):
        raise SystemExit("provider configuration or required credential does not match frozen protocol")
    budgeted = BudgetedProvider(provider, EXACT_LIVE_CALLS)

    holdout_hash = _holdout_manifest_hash(public_root)
    freeze = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": _sha256(PROJECT_ROOT / "docs" / "post-hardening-evaluation-protocol.md"),
        "runner_sha256": _sha256(PROJECT_ROOT / "scripts" / "run_post_hardening_evaluation.py"),
        "public_manifest_sha256": _sha256(public_root / "manifest.json"),
        "public_holdout_tree_sha256": holdout_hash,
        "oracle_sha256": _sha256(oracle_path),
        "git_head_at_freeze": _safe_git_head(),
        "git_status_at_freeze": _git_status(),
        "case_count": len(case_dirs),
        "faulty_case_count": sum(1 for item in oracle_cases.values() if item["faulty"]),
        "safe_case_count": sum(1 for item in oracle_cases.values() if not item["faulty"]),
        "matrix_experiments_per_case": EXPECTED_MATRIX_EXPERIMENTS,
        "product_max_experiments_per_case": PRODUCT_MAX_EXPERIMENTS,
        "authorized_live_completion_budget": EXACT_LIVE_CALLS,
        "provider": provider.provider,
        "model": provider.model,
        "reasoning_effort": provider.reasoning_effort,
        "max_output_tokens": provider.max_output_tokens,
        "max_recovery_attempts": 1,
        "credential_present": credential_present,
        "frozen_at_utc": _utc_now(),
    }
    if freeze["git_status_at_freeze"]:
        raise SystemExit("working tree must be clean at the evaluation freeze")
    _write_json(raw_root / "freeze.json", freeze)

    public_baseline_root = public_evidence / "trajectories" / "baseline"
    public_breakfix_root = public_evidence / "trajectories" / "breakfix"
    public_fixed_root = public_evidence / "fixed-matrix"
    raw_baseline_root = raw_root / "baseline"
    raw_breakfix_root = raw_root / "breakfix"
    raw_fixed_root = raw_root / "fixed-matrix"
    baseline_results: list[dict[str, Any]] = []
    baseline_telemetry: list[dict[str, Any]] = []
    breakfix_results: list[dict[str, Any]] = []
    breakfix_telemetry: list[dict[str, Any]] = []
    fixed_results: list[dict[str, Any]] = []
    breakfix_experiment_total = 0
    breakfix_regressions_valid = 0
    started_all = time.perf_counter()

    for case_root in case_dirs:
        case_id = case_root.name
        public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
        expected_outputs = oracle_cases[case_id]["expected_outputs"]

        budgeted.context_lane = "generic-baseline"
        budgeted.context_case = case_id
        prompt = render_final_generic_prompt(case_root)
        prompt_snapshot = {
            "case_id": case_id,
            "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
            "prompt_id": GENERIC_PROMPT_ID,
            "ground_truth_supplied_to_agent": False,
        }
        started = time.perf_counter()
        baseline = budgeted.complete_structured(prompt, validator=validate_phase2b_baseline_response, max_recovery_attempts=1)
        baseline_duration_ms = round((time.perf_counter() - started) * 1000)
        baseline_data = baseline.as_dict()
        parsed = baseline.parsed or {}
        recommendation = parsed.get("recommendation") if baseline.success else None
        expected_recommendation = "POTENTIAL_BREAK" if oracle_cases[case_id]["faulty"] else "NO_BREAK_FOUND"
        baseline_result = {
            "case_id": case_id,
            "recommendation": recommendation,
            "provider_status": baseline.output_contract_status,
            "valid_contract": baseline.success,
            "correct_against_external_truth": bool(baseline.success and recommendation == expected_recommendation),
            "expected_recommendation_internal": expected_recommendation,
            "duration_ms": baseline_duration_ms,
        }
        baseline_results.append(baseline_result)
        baseline_telemetry.append(_baseline_telemetry(baseline, case_id))
        _write_json(raw_baseline_root / case_id / "replay.json", {"case_id": case_id, "prompt": prompt, **prompt_snapshot, "provider_result": baseline_data, "result": baseline_result})
        _write_json(
            public_baseline_root / case_id / "replay.json",
            {
                "case_id": case_id,
                "prompt_sha256": prompt_snapshot["prompt_sha256"],
                "prompt_id": GENERIC_PROMPT_ID,
                "ground_truth_supplied_to_agent": False,
                "provider_result": baseline_data,
                "result": {
                    key: value
                    for key, value in baseline_result.items()
                    if key not in {"expected_recommendation_internal", "correct_against_external_truth"}
                },
            },
        )

        snapshot = ChangeSnapshot(
            project_root=(case_root / "after").resolve(),
            change_kind="post-hardening-holdout",
            reference=case_id,
            diff=_diff_for_case(case_root),
            changed_files=("app.py",),
            task=public["task"],
            test_command=public["test_command"],
        )
        budgeted.context_lane = "breakfix-targeted"
        budgeted.context_case = case_id
        breakfix_evidence = raw_breakfix_root / case_id
        started = time.perf_counter()
        product_analysis = analyze_change(snapshot, breakfix_evidence, provider=budgeted, max_experiments=PRODUCT_MAX_EXPERIMENTS, max_recovery_attempts=1)
        breakfix_duration_ms = round((time.perf_counter() - started) * 1000)
        breakfix_experiment_total += product_analysis.experiments_run
        if product_analysis.regression_valid:
            breakfix_regressions_valid += 1
        analysis = json.loads((breakfix_evidence / "analysis.json").read_text(encoding="utf-8"))
        provider_telemetry = json.loads((breakfix_evidence / "provider-telemetry.json").read_text(encoding="utf-8"))
        breakfix_telemetry.append({"case_id": case_id, **provider_telemetry})
        records: list[dict[str, Any]] = []
        saw_confirmed = False
        saw_error = product_analysis.provider_status in {"PROVIDER_ERROR", "PROVIDER_OUTPUT_ERROR"}
        saw_unsupported = False
        for record in analysis.get("experiment_records") or []:
            experiment_id = record["experiment_id"]
            result_path = breakfix_evidence / "experiments" / experiment_id / "result.json"
            execution = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
            oracle_result = _oracle_outcome(execution, expected_outputs, experiment_id)
            product_state = record.get("evidence_state")
            if product_state == "CONFIRMED BREAK" and oracle_result["state"] == "CONFIRMED BREAK" and record.get("evidence_sufficient") and record.get("failure_predicate_matched"):
                saw_confirmed = True
            elif product_state in {"HARNESS FAILURE", "INCONCLUSIVE", "REGRESSION INVALID"} or oracle_result["state"] == "ERROR":
                saw_error = saw_error or product_state == "HARNESS FAILURE" or oracle_result["state"] == "ERROR"
                saw_unsupported = saw_unsupported or product_state in {"INCONCLUSIVE", "REGRESSION INVALID"}
            elif product_state == "UNSUPPORTED PROBE" or oracle_result["state"] == "UNSUPPORTED":
                saw_unsupported = True
            records.append({
                "experiment_id": experiment_id,
                "state": product_state,
                "oracle_state": oracle_result["state"],
                "evidence_complete": oracle_result["evidence_complete"],
                "evidence_sufficient": record.get("evidence_sufficient"),
                "failure_predicate_matched": record.get("failure_predicate_matched"),
                "process_failed": execution.get("process_failed"),
                "duration_ms": execution.get("duration_ms"),
            })
        if saw_error or product_analysis.outcome == "ERROR":
            case_state = "ERROR"
        elif saw_confirmed:
            case_state = "CONFIRMED BREAK"
        elif not records or saw_unsupported or product_analysis.outcome == "UNSUPPORTED":
            case_state = "UNSUPPORTED"
        else:
            case_state = "NO BREAK CONFIRMED"
        breakfix_result = {
            "case_id": case_id,
            "state": case_state,
            "provider_status": product_analysis.provider_status,
            "selected_experiments": list(product_analysis.selected_experiments),
            "experiments_run": product_analysis.experiments_run,
            "regression_valid": product_analysis.regression_valid,
            "records": records,
            "duration_ms": breakfix_duration_ms,
        }
        breakfix_results.append(breakfix_result)
        _write_json(raw_breakfix_root / case_id / "evaluation.json", {**breakfix_result, "oracle": oracle_cases[case_id]})
        _copy_public_product_evidence(breakfix_evidence, public_breakfix_root / case_id)
        _write_json(public_breakfix_root / case_id / "evaluation-summary.json", breakfix_result)

    fixed_started = time.perf_counter()
    for case_root in case_dirs:
        case_id = case_root.name
        expected_outputs = oracle_cases[case_id]["expected_outputs"]
        case_result: dict[str, Any] = {"case_id": case_id, "experiments": [], "confirmed_break": False, "errors": 0, "unsupported": 0}
        for experiment in EXPERIMENTS:
            execution = run_experiment_isolated(case_root / "after", experiment.id, payload_for(experiment))
            execution_data = execution.as_dict()
            oracle_result = _oracle_outcome(execution_data, expected_outputs, experiment.id)
            item = {
                "case_id": case_id,
                "experiment_id": experiment.id,
                "state": oracle_result["state"],
                "evidence_complete": oracle_result["evidence_complete"],
                "process_failed": execution_data.get("process_failed"),
                "duration_ms": execution_data.get("duration_ms"),
            }
            case_result["experiments"].append(item)
            if oracle_result["state"] == "CONFIRMED BREAK":
                case_result["confirmed_break"] = True
            if oracle_result["state"] == "ERROR":
                case_result["errors"] += 1
            if oracle_result["state"] == "UNSUPPORTED":
                case_result["unsupported"] += 1
            target = public_fixed_root / case_id / experiment.id
            _write_json(target / "result.json", execution_data)
            _write_text(target / "stdout.log", execution.stdout)
            _write_text(target / "stderr.log", execution.stderr)
            _write_json(raw_fixed_root / case_id / experiment.id / "evaluation.json", {**item, "oracle": oracle_cases[case_id], "expected_output": expected_outputs.get(experiment.id), "actual_output": execution_data.get("output")})
        fixed_results.append(case_result)
    fixed_duration_ms = round((time.perf_counter() - fixed_started) * 1000)

    baseline_lane_results = [
        {**result, "state": "CONFIRMED BREAK" if result["recommendation"] == "POTENTIAL_BREAK" else ("NO BREAK CONFIRMED" if result["recommendation"] == "NO_BREAK_FOUND" else "ERROR")}
        for result in baseline_results
    ]
    baseline_score = _score_case_lane(baseline_lane_results, oracle_cases, lane="generic-baseline")
    fixed_case_states = [{"case_id": item["case_id"], "state": "CONFIRMED BREAK" if item["confirmed_break"] else ("ERROR" if item["errors"] else "NO BREAK CONFIRMED")} for item in fixed_results]
    fixed_score = _score_case_lane(fixed_case_states, oracle_cases, lane="fixed-matrix")
    fixed_score.update({"planned_experiments": len(case_dirs) * EXPECTED_MATRIX_EXPERIMENTS, "observed_experiments": len(fixed_results) * EXPECTED_MATRIX_EXPERIMENTS, "unsupported_probe_count": sum(item["unsupported"] for item in fixed_results), "execution_error_count": sum(item["errors"] for item in fixed_results), "duration_ms": fixed_duration_ms})
    breakfix_score = _score_case_lane(breakfix_results, oracle_cases, lane="breakfix-targeted")
    breakfix_score.update({"planned_experiments": len(case_dirs) * PRODUCT_MAX_EXPERIMENTS, "observed_experiments": breakfix_experiment_total, "max_experiments_per_case": PRODUCT_MAX_EXPERIMENTS, "regression_valid_count": breakfix_regressions_valid, "duration_ms": round((time.perf_counter() - started_all) * 1000)})
    reduction = ((fixed_score["observed_experiments"] - breakfix_score["observed_experiments"]) / fixed_score["observed_experiments"] * 100) if fixed_score["eligible"] and breakfix_score["eligible"] else None
    per_defect = breakfix_score["observed_experiments"] / breakfix_score["confirmed_fault_cases"] if breakfix_score["eligible"] and breakfix_score["confirmed_fault_cases"] else None
    total_telemetry = _aggregate_telemetry(baseline_telemetry + breakfix_telemetry)
    gate = "PASS" if fixed_score["eligible"] and breakfix_score["eligible"] and breakfix_score["observed_experiments"] < fixed_score["observed_experiments"] and budgeted.calls == EXACT_LIVE_CALLS else "FAIL"
    summary = {
        "run_id": run_id,
        "protocol_id": PROTOCOL_ID,
        "protocol_status": "frozen before evaluation",
        "product_checkpoint": freeze["git_head_at_freeze"],
        "git_head_at_start": freeze["git_head_at_freeze"],
        "git_status_at_start": freeze["git_status_at_freeze"],
        "history_free_workspace": str(workspace),
        "public_holdout_root": str(public_root),
        "private_oracle_path": str(oracle_path),
        "deepseek_credential_present": credential_present,
        "started_at_utc": _utc_now(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "holdout_case_count": len(case_dirs),
        "faulty_case_count": sum(1 for item in oracle_cases.values() if item["faulty"]),
        "safe_case_count": sum(1 for item in oracle_cases.values() if not item["faulty"]),
        "public_manifest_sha256": freeze["public_manifest_sha256"],
        "holdout_manifest_sha256": freeze["public_holdout_tree_sha256"],
        "oracle_sha256": freeze["oracle_sha256"],
        "runner_sha256": freeze["runner_sha256"],
        "protocol_sha256": freeze["protocol_sha256"],
        "leakage_audit": leakage,
        "history_free_workspace_audit": workspace_audit,
        "visible_fixture_tests": {"case_count": len(visible_results), "passed_cases": sum(1 for item in visible_results if item.get("exit_code") == 0 and not item.get("process_failed") and not item.get("timed_out"))},
        "current_unit_tests": {"exit_code": current_tests.exit_code, "process_failed": current_tests.process_failed, "timed_out": current_tests.timed_out, "stdout": current_tests.stdout, "stderr": current_tests.stderr},
        "baseline": baseline_score,
        "fixed_matrix": fixed_score,
        "breakfix": breakfix_score,
        "experiment_reduction_percentage": reduction,
        "experiments_per_confirmed_defect": per_defect,
        "primary_gate": gate,
        "live_provider_completion_calls": budgeted.calls,
        "live_provider_call_log": budgeted.call_log,
        "telemetry": {"baseline": _aggregate_telemetry(baseline_telemetry), "breakfix": _aggregate_telemetry(breakfix_telemetry), "all_live_provider_calls": total_telemetry},
        "live_case_results": {"baseline": baseline_results, "breakfix": breakfix_results},
        "fixed_case_results": fixed_results,
    }
    _write_json(raw_root / "final-summary.json", summary)
    public_summary = json.loads(json.dumps(summary))
    for key in ("private_oracle_path", "history_free_workspace", "live_provider_call_log"):
        public_summary.pop(key, None)
    for item in public_summary["live_case_results"]["baseline"]:
        item.pop("expected_recommendation_internal", None)
        item.pop("correct_against_external_truth", None)
    _write_json(public_evidence / "final-summary.json", public_summary)
    _write_json(public_evidence / "leakage-audit.json", {"public_holdout": leakage, "history_free_workspace": workspace_audit})
    _write_json(public_evidence / "run-metadata.json", {
        "run_id": run_id,
        "protocol_id": PROTOCOL_ID,
        "product_checkpoint": freeze["git_head_at_freeze"],
        "protocol_sha256": freeze["protocol_sha256"],
        "runner_sha256": freeze["runner_sha256"],
        "public_manifest_sha256": freeze["public_manifest_sha256"],
        "holdout_manifest_sha256": freeze["public_holdout_tree_sha256"],
        "oracle_sha256": freeze["oracle_sha256"],
        "public_holdout_cases": len(case_dirs),
        "truth_loaded_externally": True,
        "truth_path_published": False,
        "git_head_at_start": freeze["git_head_at_freeze"],
        "deepseek_credential_present": credential_present,
        "live_provider_completion_calls": budgeted.calls,
    })
    print(json.dumps({"run_id": run_id, "primary_gate": gate, "live_provider_completion_calls": budgeted.calls, "baseline": baseline_score, "fixed_matrix": fixed_score, "breakfix": breakfix_score, "experiment_reduction_percentage": reduction, "public_evidence": str(public_evidence), "raw_evidence": str(raw_root)}, indent=2))


if __name__ == "__main__":
    main()
