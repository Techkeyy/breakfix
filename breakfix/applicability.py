from __future__ import annotations

from typing import Any

from .evidence_contract import validate_structured_failure_predicate
from .models import Experiment


# The shipped executor runs a Python target process. It has no browser event,
# DOM, download, or filesystem-observer capability. Keep this list deliberately
# conservative: a browser-specific assumption must never be treated as a
# generic Python perturbation.
BROWSER_HYPOTHESIS_TERMS = (
    "browser",
    "blob",
    "download",
    "dom",
    "anchor",
    "object url",
    "revokeobjecturl",
    "programmatic download",
    "document.",
)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    return ""


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_target(value: Any) -> bool:
    if _non_empty_text(value):
        return True
    if not isinstance(value, dict):
        return False
    return any(_non_empty_text(value.get(field)) for field in ("file", "symbol", "runtime_boundary"))


def assess_probe_applicability(
    assumption: dict[str, Any],
    proposal: dict[str, Any],
    experiment: Experiment | None,
) -> dict[str, Any]:
    """Check the causal contract before a proposed probe can execute.

    This is intentionally a conservative gate. A matching broad surface is
    not enough; the assumption must name the semantic family exercised by the
    concrete catalogue probe, and the proposal must describe the condition,
    observable, predicate, and rationale that will be used before execution.
    """
    required = (
        "target",
        "hypothesis",
        "perturbation",
        "observable",
        "failure_predicate",
        "why_this_probe_tests_this_assumption",
        "structured_failure_predicate",
    )
    if experiment is None:
        return {
            "applicable": False,
            "status": "UNSUPPORTED",
            "reason": "experiment is outside the supported execution catalogue",
        }
    missing = [field for field in required if field not in proposal]
    if missing:
        return {
            "applicable": False,
            "status": "NOT EXECUTABLE",
            "reason": f"semantic experiment contract is missing: {', '.join(missing)}",
        }
    if not _valid_target(proposal.get("target")):
        return {"applicable": False, "status": "NOT EXECUTABLE", "reason": "target must identify a file, symbol, or runtime boundary"}
    for field in ("hypothesis", "observable", "failure_predicate", "why_this_probe_tests_this_assumption"):
        if not _non_empty_text(proposal.get(field)):
            return {"applicable": False, "status": "NOT EXECUTABLE", "reason": f"{field} must be a non-empty string"}
    if not isinstance(proposal.get("perturbation"), dict):
        return {"applicable": False, "status": "NOT EXECUTABLE", "reason": "perturbation must be an object"}
    if proposal["perturbation"] != experiment.perturbation:
        return {
            "applicable": False,
            "status": "NOT EXECUTABLE",
            "reason": "proposed perturbation does not match the concrete catalogue condition",
        }
    structured_predicate = validate_structured_failure_predicate(
        proposal.get("structured_failure_predicate"), experiment
    )
    if not structured_predicate.get("valid"):
        return {
            "applicable": False,
            "status": "NOT EXECUTABLE",
            "reason": structured_predicate.get("reason", "structured failure predicate is not executable"),
            "structured_predicate_validation": structured_predicate,
        }
    # For structured output, the typed predicate is the machine-checkable
    # contract. The catalogue prose remains explanatory context and must not
    # reject a semantically compatible planner description. Exception-only
    # probes retain the deterministic prose contract because there is no
    # structured marker to evaluate.
    if structured_predicate.get("predicate") is None and (
        proposal["failure_predicate"].strip().lower() != experiment.failure_predicate.strip().lower()
    ):
        return {
            "applicable": False,
            "status": "NOT EXECUTABLE",
            "reason": "exception-only failure predicate does not match the deterministic catalogue contract",
        }
    if assumption.get("surface") != experiment.surface:
        return {
            "applicable": False,
            "status": "NOT EXECUTABLE",
            "reason": f"assumption surface {assumption.get('surface')!r} does not match probe surface {experiment.surface!r}",
        }

    assumption_text = " ".join(
        (
            _text(assumption.get("statement")),
            _text(assumption.get("failure_if_false")),
            _text(assumption.get("evidence")),
        )
    )
    browser_terms = [term for term in BROWSER_HYPOTHESIS_TERMS if term in assumption_text]
    if browser_terms and experiment.capability != "browser-observable":
        return {
            "applicable": False,
            "status": "UNSUPPORTED",
            "reason": "browser-specific hypothesis requires an unavailable browser-observable execution capability",
            "browser_terms": browser_terms,
        }
    matches = [term for term in experiment.match_terms if term in assumption_text]
    if not matches:
        return {
            "applicable": False,
            "status": "NOT EXECUTABLE",
            "reason": "assumption semantics do not establish that this probe tests the claimed failure mode",
        }
    return {
        "applicable": True,
        "status": "CANDIDATE",
        "reason": "assumption semantics, probe surface, perturbation, observable, and failure predicate align",
        "matched_terms": matches,
        "capability": experiment.capability,
        "structured_failure_predicate": structured_predicate.get("predicate"),
    }
