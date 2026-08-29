from __future__ import annotations

import json
from typing import Any

from .experiments import EXPERIMENTS


SUPPORTED_EXPERIMENTS = {experiment.id: experiment for experiment in EXPERIMENTS}
SUPPORTED_SURFACES = {"input", "state", "timing", "world"}
SUPPORTED_RISKS = {"low", "medium", "high"}


def _json_object(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one JSON object from a model response without inventing fields."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        for index, character in enumerate(stripped):
            if character != "{":
                continue
            try:
                value, end = decoder.raw_decode(stripped[index:])
            except json.JSONDecodeError:
                continue
            if stripped[index + end :].strip():
                continue
            break
        else:
            return None, f"invalid JSON: {exc.msg} at character {exc.pos}"
    if not isinstance(value, dict):
        return None, "model response must be a JSON object"
    return value, None


def validate_baseline_response(text: str) -> dict[str, Any]:
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {
            "valid": False,
            "parse_error": parse_error,
            "raw_response": text,
            "findings": [],
        }
    assert parsed is not None
    failures: list[str] = []
    decision = parsed.get("decision")
    if decision not in {"accept", "needs-review", "inconclusive"}:
        failures.append("decision must be accept, needs-review, or inconclusive")
    findings = parsed.get("findings")
    if not isinstance(findings, list):
        failures.append("findings must be a list")
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            failures.append(f"finding {index} must be an object")
            continue
        if not isinstance(finding.get("summary"), str):
            failures.append(f"finding {index} is missing a string summary")
        if not isinstance(finding.get("evidence"), list):
            failures.append(f"finding {index} is missing an evidence list")
    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "decision": decision,
        "findings": findings if not failures else [],
    }


def validate_breakfix_response(text: str) -> dict[str, Any]:
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {
            "valid": False,
            "parse_error": parse_error,
            "raw_response": text,
            "assumptions": [],
            "selected_experiment_ids": [],
            "unsupported_assumptions": [],
        }
    assert parsed is not None
    failures: list[str] = []
    assumptions = parsed.get("assumptions")
    if not isinstance(parsed.get("change_summary"), str):
        failures.append("change_summary must be a string")
    if not isinstance(assumptions, list):
        failures.append("assumptions must be a list")
        assumptions = []

    valid_assumptions: list[dict[str, Any]] = []
    selected: list[str] = []
    unsupported: list[dict[str, Any]] = []
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            failures.append(f"assumption {index} must be an object")
            continue
        required = ("id", "statement", "surface", "evidence", "failure_if_false", "risk", "proposed_experiment")
        missing = [field for field in required if field not in assumption]
        if missing:
            failures.append(f"assumption {index} missing fields: {', '.join(missing)}")
            continue
        if assumption["surface"] not in SUPPORTED_SURFACES:
            failures.append(f"assumption {index} has unsupported surface {assumption['surface']!r}")
        if assumption["risk"] not in SUPPORTED_RISKS:
            failures.append(f"assumption {index} has unsupported risk {assumption['risk']!r}")
        if not isinstance(assumption["evidence"], list):
            failures.append(f"assumption {index} evidence must be a list")
        proposed = assumption["proposed_experiment"]
        if not isinstance(proposed, dict) or not isinstance(proposed.get("id"), str):
            failures.append(f"assumption {index} proposed_experiment must contain an id")
            continue
        experiment_id = proposed["id"]
        record = {**assumption, "supported_experiment": experiment_id in SUPPORTED_EXPERIMENTS}
        if experiment_id not in SUPPORTED_EXPERIMENTS:
            record["unsupported_reason"] = "experiment id is outside the supported perturbation catalogue"
            unsupported.append(record)
        elif experiment_id not in selected:
            selected.append(experiment_id)
        valid_assumptions.append(record)

    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "change_summary": parsed.get("change_summary"),
        "assumptions": valid_assumptions if not failures else [],
        "selected_experiment_ids": selected if not failures else [],
        "unsupported_assumptions": unsupported if not failures else [],
        "supported_catalogue": [experiment.id for experiment in EXPERIMENTS],
    }


def validate_phase2a_baseline_response(text: str) -> dict[str, Any]:
    """Validate the frozen Phase 2A baseline verdict contract."""
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {
            "valid": False,
            "parse_error": parse_error,
            "raw_response": text,
            "verdict": None,
            "findings": [],
        }
    assert parsed is not None
    failures: list[str] = []
    verdict = parsed.get("verdict")
    if verdict not in {"DEFECT", "SAFE", "INCONCLUSIVE"}:
        failures.append("verdict must be DEFECT, SAFE, or INCONCLUSIVE")
    if not isinstance(parsed.get("change_summary"), str):
        failures.append("change_summary must be a string")
    findings = parsed.get("findings")
    if not isinstance(findings, list):
        failures.append("findings must be a list")
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            failures.append(f"finding {index} must be an object")
            continue
        if not isinstance(finding.get("summary"), str):
            failures.append(f"finding {index} is missing a string summary")
        if not isinstance(finding.get("evidence"), list):
            failures.append(f"finding {index} is missing an evidence list")
    for field in ("tests_run", "tool_actions"):
        if not isinstance(parsed.get(field), list):
            failures.append(f"{field} must be a list")
    if not isinstance(parsed.get("final_conclusion"), str):
        failures.append("final_conclusion must be a string")
    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "verdict": verdict if not failures else None,
        "findings": findings if not failures else [],
    }


def validate_phase2a_breakfix_response(text: str) -> dict[str, Any]:
    """Validate Phase 2A assumptions without allowing the model to decide success."""
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {
            "valid": False,
            "parse_error": parse_error,
            "raw_response": text,
            "assumptions": [],
            "selected_experiment_ids": [],
            "unsupported_assumptions": [],
        }
    assert parsed is not None
    failures: list[str] = []
    if not isinstance(parsed.get("change_summary"), str):
        failures.append("change_summary must be a string")
    assumptions = parsed.get("assumptions")
    if not isinstance(assumptions, list):
        failures.append("assumptions must be a list")
        assumptions = []
    for field in ("tests_run", "tool_actions"):
        if not isinstance(parsed.get(field), list):
            failures.append(f"{field} must be a list")
    if not isinstance(parsed.get("final_conclusion"), str):
        failures.append("final_conclusion must be a string")

    valid_assumptions: list[dict[str, Any]] = []
    selected: list[str] = []
    unsupported: list[dict[str, Any]] = []
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            failures.append(f"assumption {index} must be an object")
            continue
        required = ("id", "statement", "surface", "evidence", "failure_if_false", "risk", "proposed_experiment")
        missing = [field for field in required if field not in assumption]
        if missing:
            failures.append(f"assumption {index} missing fields: {', '.join(missing)}")
            continue
        if not isinstance(assumption["id"], str) or not isinstance(assumption["statement"], str):
            failures.append(f"assumption {index} id and statement must be strings")
        if assumption["surface"] not in SUPPORTED_SURFACES:
            failures.append(f"assumption {index} has unsupported surface {assumption['surface']!r}")
        if assumption["risk"] not in SUPPORTED_RISKS:
            failures.append(f"assumption {index} has unsupported risk {assumption['risk']!r}")
        if not isinstance(assumption["evidence"], list):
            failures.append(f"assumption {index} evidence must be a list")
        proposed = assumption["proposed_experiment"]
        if not isinstance(proposed, dict) or not isinstance(proposed.get("id"), str):
            failures.append(f"assumption {index} proposed_experiment must contain an id")
            continue
        experiment_id = proposed["id"]
        record = {**assumption, "supported_experiment": experiment_id in SUPPORTED_EXPERIMENTS}
        if experiment_id not in SUPPORTED_EXPERIMENTS:
            record["unsupported_reason"] = "experiment id is outside the supported perturbation catalogue"
            unsupported.append(record)
        elif experiment_id not in selected:
            selected.append(experiment_id)
        valid_assumptions.append(record)
    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "assumptions": valid_assumptions if not failures else [],
        "selected_experiment_ids": selected if not failures else [],
        "unsupported_assumptions": unsupported if not failures else [],
        "supported_catalogue": [experiment.id for experiment in EXPERIMENTS],
    }


def validate_phase2b_baseline_response(text: str) -> dict[str, Any]:
    """Validate the Phase 2B reasoning-only comparator contract."""
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {"valid": False, "parse_error": parse_error, "raw_response": text, "recommendation": None, "findings": []}
    assert parsed is not None
    failures: list[str] = []
    recommendation = parsed.get("recommendation")
    if recommendation not in {"POTENTIAL_BREAK", "NO_BREAK_FOUND", "INCONCLUSIVE"}:
        failures.append("recommendation must be POTENTIAL_BREAK, NO_BREAK_FOUND, or INCONCLUSIVE")
    if not isinstance(parsed.get("change_summary"), str):
        failures.append("change_summary must be a string")
    findings = parsed.get("findings")
    if not isinstance(findings, list):
        failures.append("findings must be a list")
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            failures.append(f"finding {index} must be an object")
            continue
        if not isinstance(finding.get("summary"), str):
            failures.append(f"finding {index} is missing a string summary")
        if not isinstance(finding.get("evidence"), list):
            failures.append(f"finding {index} is missing an evidence list")
    for field in ("tests_run", "tool_actions"):
        if not isinstance(parsed.get(field), list):
            failures.append(f"{field} must be a list")
    if not isinstance(parsed.get("final_conclusion"), str):
        failures.append("final_conclusion must be a string")
    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "recommendation": recommendation if not failures else None,
        "findings": findings if not failures else [],
    }


def validate_phase2b_breakfix_response(text: str) -> dict[str, Any]:
    """Validate ranked Phase 2B assumptions without allowing model verdicts."""
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {
            "valid": False,
            "parse_error": parse_error,
            "raw_response": text,
            "assumptions": [],
            "unsupported_assumptions": [],
        }
    assert parsed is not None
    failures: list[str] = []
    if not isinstance(parsed.get("change_summary"), str):
        failures.append("change_summary must be a string")
    assumptions = parsed.get("assumptions")
    if not isinstance(assumptions, list):
        failures.append("assumptions must be a list")
        assumptions = []
    for field in ("tests_run", "tool_actions"):
        if not isinstance(parsed.get(field), list):
            failures.append(f"{field} must be a list")
    if not isinstance(parsed.get("final_conclusion"), str):
        failures.append("final_conclusion must be a string")

    valid_assumptions: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            failures.append(f"assumption {index} must be an object")
            continue
        required = ("id", "statement", "surface", "evidence", "failure_if_false", "risk", "proposed_experiment")
        missing = [field for field in required if field not in assumption]
        if missing:
            failures.append(f"assumption {index} missing fields: {', '.join(missing)}")
            continue
        if not isinstance(assumption["id"], str) or not isinstance(assumption["statement"], str):
            failures.append(f"assumption {index} id and statement must be strings")
        if assumption["surface"] not in SUPPORTED_SURFACES:
            failures.append(f"assumption {index} has unsupported surface {assumption['surface']!r}")
        if assumption["risk"] not in SUPPORTED_RISKS:
            failures.append(f"assumption {index} has unsupported risk {assumption['risk']!r}")
        if not isinstance(assumption["evidence"], list):
            failures.append(f"assumption {index} evidence must be a list")
        proposed = assumption["proposed_experiment"]
        if not isinstance(proposed, dict) or not isinstance(proposed.get("id"), str):
            failures.append(f"assumption {index} proposed_experiment must contain an id")
            continue
        experiment_id = proposed["id"]
        record = {**assumption, "supported_experiment": experiment_id in SUPPORTED_EXPERIMENTS}
        if experiment_id not in SUPPORTED_EXPERIMENTS:
            record["unsupported_reason"] = "experiment id is outside the supported perturbation catalogue"
            unsupported.append(record)
        valid_assumptions.append(record)
    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "assumptions": valid_assumptions if not failures else [],
        "unsupported_assumptions": unsupported if not failures else [],
        "supported_catalogue": [experiment.id for experiment in EXPERIMENTS],
    }


def validate_product_planner_response(text: str) -> dict[str, Any]:
    """Validate the compact planner contract used by the shipped product.

    The model may suggest probes, but it never decides whether a break exists.
    Only deterministic execution in the engine can produce a product verdict.
    """
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {
            "valid": False,
            "parse_error": parse_error,
            "raw_response": text,
            "assumptions": [],
            "selected_experiment_ids": [],
            "unsupported_assumptions": [],
        }
    assert parsed is not None
    failures: list[str] = []
    if not isinstance(parsed.get("change_summary"), str):
        failures.append("change_summary must be a string")
    assumptions = parsed.get("assumptions")
    if not isinstance(assumptions, list):
        failures.append("assumptions must be a list")
        assumptions = []

    valid_assumptions: list[dict[str, Any]] = []
    selected: list[str] = []
    unsupported: list[dict[str, Any]] = []
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            failures.append(f"assumption {index} must be an object")
            continue
        required = ("id", "statement", "surface", "risk", "evidence", "failure_if_false", "experiment")
        missing = [field for field in required if field not in assumption]
        if missing:
            failures.append(f"assumption {index} missing fields: {', '.join(missing)}")
            continue
        if not isinstance(assumption["id"], str) or not isinstance(assumption["statement"], str):
            failures.append(f"assumption {index} id and statement must be strings")
        if assumption["surface"] not in SUPPORTED_SURFACES:
            failures.append(f"assumption {index} has unsupported surface {assumption['surface']!r}")
        if assumption["risk"] not in SUPPORTED_RISKS:
            failures.append(f"assumption {index} has unsupported risk {assumption['risk']!r}")
        evidence = assumption["evidence"]
        if not isinstance(evidence, list) or not all(isinstance(item, dict) for item in evidence):
            failures.append(f"assumption {index} evidence must be a list of objects")
        experiment = assumption["experiment"]
        if not isinstance(experiment, dict) or not isinstance(experiment.get("type"), str):
            failures.append(f"assumption {index} experiment must contain a string type")
            continue
        experiment_id = experiment["type"]
        record = {**assumption, "supported_experiment": experiment_id in SUPPORTED_EXPERIMENTS}
        if experiment_id not in SUPPORTED_EXPERIMENTS:
            record["unsupported_reason"] = "experiment type is outside the supported perturbation catalogue"
            unsupported.append(record)
        elif experiment_id not in selected:
            selected.append(experiment_id)
        valid_assumptions.append(record)

    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
        "change_summary": parsed.get("change_summary"),
        "assumptions": valid_assumptions if not failures else [],
        "selected_experiment_ids": selected if not failures else [],
        "unsupported_assumptions": unsupported if not failures else [],
        "supported_catalogue": [experiment.id for experiment in EXPERIMENTS],
    }


def validate_fix_response(text: str) -> dict[str, Any]:
    """Validate a proposed patch without applying or trusting model claims."""
    parsed, parse_error = _json_object(text)
    if parse_error:
        return {"valid": False, "parse_error": parse_error, "raw_response": text}
    assert parsed is not None
    failures: list[str] = []
    for field in ("summary", "patch"):
        if not isinstance(parsed.get(field), str) or not parsed[field].strip():
            failures.append(f"{field} must be a non-empty string")
    if not isinstance(parsed.get("files_changed"), list) or not all(isinstance(item, str) for item in parsed["files_changed"]):
        failures.append("files_changed must be a list of strings")
    if not isinstance(parsed.get("tests_to_run"), list) or not all(isinstance(item, str) for item in parsed["tests_to_run"]):
        failures.append("tests_to_run must be a list of strings")
    return {
        "valid": not failures,
        "validation_failures": failures,
        "parsed": parsed if not failures else None,
        "raw_response": text,
    }
