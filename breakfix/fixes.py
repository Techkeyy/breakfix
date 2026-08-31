from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .agent_contract import validate_fix_response
from .evidence import write_json, write_text
from .executor import isolated_copy, run_command, run_experiment_isolated
from .product import _regression_command
from .provider import DirectProvider, StructuredProviderResult


def _load_confirmed(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    analysis = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
    confirmed = next(
        (record for record in analysis.get("experiment_records", []) if record.get("evidence_state") == "CONFIRMED BREAK"),
        None,
    )
    if confirmed is None:
        raise RuntimeError("evidence does not contain a confirmed break")
    if not confirmed.get("evidence_sufficient") or not confirmed.get("failure_predicate_matched"):
        raise RuntimeError("confirmed evidence does not satisfy the hardened evidence contract")
    return analysis, confirmed


def _prompt(root: Path, analysis: dict[str, Any], confirmed: dict[str, Any]) -> str:
    project = Path(analysis.get("project_snapshot") or analysis["project_root"])
    source = []
    for path in sorted(project.rglob("*.py")):
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        source.append(f"### {path.relative_to(project).as_posix()}\n{path.read_text(encoding='utf-8', errors='replace')[:20000]}")
        if len(source) >= 8:
            break
    return f"""You are proposing a candidate fix for a confirmed deterministic BreakFix failure.

The candidate must be a unified diff only for the files it changes. Do not
apply it, claim it is verified, or include markdown outside the JSON object.
The human must review and approve it before any application.

Return exactly:
{{
  "summary": "short explanation",
  "patch": "unified diff text",
  "files_changed": ["path"],
  "tests_to_run": ["command"],
  "evidence_reference": "the confirmed experiment id and concrete observable",
  "causal_explanation": "confirmed evidence -> causal condition -> changed code"
}}

Failure evidence:
{json.dumps(confirmed, indent=2)}

The evidence_reference must name the confirmed experiment and observable. The
causal_explanation must connect that evidence to the exact failure condition
and to the proposed code change. Do not inflate a timeout, retry count, or
other parameter without confirmed evidence requiring it.

Project files:
{chr(10).join(source)}
"""


def propose_fix(evidence_dir: Path, *, provider: DirectProvider | None = None) -> dict[str, Any]:
    root = evidence_dir.resolve()
    analysis, confirmed = _load_confirmed(root)
    provider = provider or DirectProvider()
    prompt = _prompt(root, analysis, confirmed)
    write_text(root / "fix" / "proposal-prompt.txt", prompt)
    result = provider.complete_structured(prompt, validator=validate_fix_response, max_recovery_attempts=1)
    write_json(root / "fix" / "provider-recovery.json", result.as_dict())
    proposal = result.parsed if isinstance(result.parsed, dict) else None
    confirmed_id = str(confirmed.get("experiment_id") or "")
    evidence_reference = proposal.get("evidence_reference") if proposal else None
    causal_explanation = proposal.get("causal_explanation") if proposal else None
    causal_valid = bool(
        result.success
        and isinstance(evidence_reference, str)
        and confirmed_id
        and confirmed_id in evidence_reference
        and isinstance(causal_explanation, str)
        and causal_explanation.strip()
    )
    causal_reason = (
        "proposal explicitly references the confirmed experiment and explains the evidence-to-cause-to-code chain"
        if causal_valid
        else "proposal does not establish a causal link to the confirmed experiment"
    )
    payload = {
        "status": "PROPOSED" if causal_valid else ("DECLINED" if result.success else "ERROR"),
        "human_approval_required": True,
        "proposal": proposal if causal_valid else None,
        "failure_code": None if causal_valid else ("FIX_CAUSALITY_UNPROVEN" if result.success else result.failure_code),
        "causal_contract": {
            "valid": causal_valid,
            "confirmed_experiment_id": confirmed_id,
            "evidence_reference": evidence_reference,
            "causal_explanation": causal_explanation,
            "reason": causal_reason,
        },
    }
    write_json(root / "fix" / "proposal.json", payload)
    return payload


def _apply_patch(snapshot: Path, patch: str) -> dict[str, Any]:
    """Apply a reviewed unified diff without requiring a Git repository."""
    lines = patch.splitlines()
    files: list[tuple[str, list[tuple[list[str], list[str]]]]] = []
    current_path: str | None = None
    hunks: list[tuple[list[str], list[str]]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("+++ b/"):
            if current_path is not None:
                files.append((current_path, hunks))
            current_path = line[6:]
            hunks = []
            index += 1
            continue
        if line.startswith("@@"):
            old_block: list[str] = []
            new_block: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@", "--- ", "+++ ")):
                entry = lines[index]
                if entry.startswith(" "):
                    old_block.append(entry[1:])
                    new_block.append(entry[1:])
                elif entry.startswith("-"):
                    old_block.append(entry[1:])
                elif entry.startswith("+"):
                    new_block.append(entry[1:])
                index += 1
            hunks.append((old_block, new_block))
            continue
        index += 1
    if current_path is not None:
        files.append((current_path, hunks))
    if not files or any(not hunks for _, hunks in files):
        return {"exit_code": 1, "stdout": "", "stderr": "patch did not contain applicable unified hunks", "applied": False}

    originals: dict[Path, str] = {}
    updated: dict[Path, list[str]] = {}
    try:
        for relative, hunks in files:
            path = (snapshot / relative).resolve()
            if snapshot.resolve() not in path.parents:
                raise ValueError(f"patch path escapes approved snapshot: {relative}")
            if not path.is_file():
                raise FileNotFoundError(relative)
            original = path.read_text(encoding="utf-8")
            originals[path] = original
            content = original.splitlines()
            cursor = 0
            for old_block, new_block in hunks:
                found = -1
                for candidate in range(cursor, len(content) - len(old_block) + 1):
                    if content[candidate : candidate + len(old_block)] == old_block:
                        found = candidate
                        break
                if found < 0:
                    raise ValueError(f"hunk context did not match {relative}")
                content[found : found + len(old_block)] = deepcopy(new_block)
                cursor = found + len(new_block)
            updated[path] = content
        for path, content in updated.items():
            path.write_text("\n".join(content) + ("\n" if originals[path].endswith(("\n", "\r")) else ""), encoding="utf-8")
    except Exception as exc:
        return {"exit_code": 1, "stdout": "", "stderr": str(exc), "applied": False}
    return {"exit_code": 0, "stdout": "", "stderr": "", "applied": True}


def apply_fix(evidence_dir: Path, *, approved: bool = False) -> dict[str, Any]:
    if not approved:
        raise PermissionError("human approval is required; pass --approved explicitly")
    root = evidence_dir.resolve()
    analysis, _confirmed = _load_confirmed(root)
    proposal = json.loads((root / "fix" / "proposal.json").read_text(encoding="utf-8"))
    if (
        proposal.get("status") != "PROPOSED"
        or not isinstance(proposal.get("proposal"), dict)
        or not isinstance(proposal.get("causal_contract"), dict)
        or proposal["causal_contract"].get("valid") is not True
    ):
        raise RuntimeError("no valid fix proposal is available")
    patch = proposal["proposal"].get("patch")
    if not isinstance(patch, str) or not patch.strip():
        raise RuntimeError("fix proposal does not contain a patch")
    source = Path(analysis.get("project_snapshot") or analysis["project_root"])
    target = root / "approved_snapshot"
    if not target.exists():
        from .executor import copy_sanitized_project

        copy_sanitized_project(source, target)
    applied = _apply_patch(target, patch)
    result = {
        "approved": True,
        "target": str(target),
        **applied,
    }
    write_json(root / "fix" / "application.json", result)
    return result


def verify_fix(evidence_dir: Path) -> dict[str, Any]:
    root = evidence_dir.resolve()
    analysis, confirmed = _load_confirmed(root)
    target = root / "approved_snapshot"
    if not target.is_dir():
        raise RuntimeError("approved snapshot is missing; review and apply a fix first")
    experiment = run_experiment_isolated(target, confirmed["experiment_id"], confirmed["payload"])
    visible = None
    if analysis.get("test_command"):
        with isolated_copy(target) as sandbox:
            visible = run_command(sandbox, analysis["test_command"], label="verified_visible_tests", timeout_seconds=45)
    regression = None
    regression_file = root / "regression" / "test_breakfix_regression.py"
    if regression_file.is_file():
        broken_run = {}
        broken_run_path = root / "regression" / "broken-run.json"
        if broken_run_path.is_file():
            try:
                broken_run = json.loads(broken_run_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                broken_run = {}
        command = broken_run.get("command_used") if isinstance(broken_run.get("command_used"), list) else _regression_command(regression_file.name)
        with isolated_copy(target) as sandbox:
            tests_dir = sandbox / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / regression_file.name).write_text(regression_file.read_text(encoding="utf-8"), encoding="utf-8")
            regression = run_command(sandbox, command, label="verified_regression", timeout_seconds=45)
    exact_reproduction_cleared = bool(
        experiment.failure_kind == "TARGET_SUCCESS" and experiment.output_captured
    )
    generated_regression_passes = bool(
        regression is not None
        and regression.exit_code == 0
        and not regression.timed_out
        and not regression.harness_failed
    )
    relevant_original_tests_pass = bool(
        visible is not None
        and visible.exit_code == 0
        and not visible.timed_out
        and not visible.harness_failed
    )
    checks = {
        "exact_confirmed_reproduction_cleared": exact_reproduction_cleared,
        "generated_regression_passes": generated_regression_passes,
        "relevant_original_tests_pass": relevant_original_tests_pass,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    verified = not failed_checks
    result = {
        "status": "VERIFIED" if verified else "NOT VERIFIED",
        "experiment": experiment.as_dict(),
        "visible_tests": visible.as_dict() if visible else None,
        "regression": regression.as_dict() if regression else None,
        "checks": checks,
        "failed_checks": failed_checks,
        "failure_reason": None if verified else "verification checks failed: " + ", ".join(failed_checks),
        "user_message": (
            "The proposed fix satisfied BreakFix's verification checks and has been accepted as a verified resolution."
            if verified
            else "The proposed fix did not satisfy BreakFix's verification checks. It has not been accepted as a verified resolution."
        ),
        "candidate_fix_rejected_by_verification": not verified,
    }
    write_json(root / "fix" / "verification.json", result)
    return result
