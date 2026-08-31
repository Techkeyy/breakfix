from __future__ import annotations

import math
from typing import Any


# Equality is sufficient for every currently supported structured failure
# marker. Keeping the set this small prevents the planner from smuggling in
# arbitrary expressions or fuzzy comparisons.
ALLOWED_STRUCTURED_OPERATORS = ("equals",)


def _json_type_matches(value: Any, expected: Any) -> bool:
    expected_types = expected if isinstance(expected, list) else [expected]
    for expected_type in expected_types:
        if expected_type == "null" and value is None:
            return True
        if expected_type == "boolean" and isinstance(value, bool):
            return True
        if expected_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if expected_type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return not isinstance(value, float) or math.isfinite(value)
        if expected_type == "string" and isinstance(value, str):
            return True
    return False


def _failure(predicate: Any, reason: str) -> dict[str, Any]:
    return {"valid": False, "predicate": None, "reason": reason}


def _schema_at_path(schema: Any, path: list[str]) -> dict[str, Any] | None:
    """Resolve one canonical array path through an object JSON schema."""
    current = schema
    for index, part in enumerate(path):
        if not isinstance(current, dict):
            return None
        properties = current.get("properties")
        if not isinstance(properties, dict) or part not in properties:
            return None
        current = properties[part]
        if index < len(path) - 1:
            declared_types = current.get("type") if isinstance(current, dict) else None
            declared_types = declared_types if isinstance(declared_types, list) else [declared_types]
            if "object" not in declared_types:
                return None
    return current if isinstance(current, dict) else None


def validate_structured_failure_predicate(predicate: Any, experiment: Any) -> dict[str, Any]:
    """Validate a typed output predicate against one experiment capability."""
    if predicate is None:
        return {"valid": True, "predicate": None, "reason": "no structured-output predicate; exception evidence only"}
    if not isinstance(predicate, dict):
        return _failure(predicate, "structured_failure_predicate must be an object or null")
    required = {"path", "operator", "value"}
    missing = sorted(required - set(predicate))
    if missing:
        return _failure(predicate, f"structured_failure_predicate missing fields: {', '.join(missing)}")
    if set(predicate) != required:
        return _failure(predicate, "structured_failure_predicate contains unsupported fields")
    path = predicate.get("path")
    if not isinstance(path, list) or not path or not all(isinstance(part, str) and part for part in path):
        return _failure(predicate, "structured predicate path must be a non-empty list of strings")
    operator = predicate.get("operator")
    allowed_operators = tuple(getattr(experiment, "allowed_predicate_operators", ()) or ())
    if operator not in allowed_operators or operator not in ALLOWED_STRUCTURED_OPERATORS:
        return _failure(predicate, f"structured predicate operator {operator!r} is not allowed for this probe family")
    schema = getattr(experiment, "observable_schema", {}) or {}
    field_schema = _schema_at_path(schema, path)
    if field_schema is None:
        return _failure(predicate, f"structured predicate path {path!r} is not declared by the observable schema")
    expected_type = field_schema.get("type") if isinstance(field_schema, dict) else None
    field = ".".join(path)
    if not _json_type_matches(predicate.get("value"), expected_type):
        return _failure(predicate, f"structured predicate value does not match the declared type for {field!r}")
    return {
        "valid": True,
        "predicate": {"path": list(path), "operator": operator, "value": predicate.get("value")},
        "reason": "structured predicate matches the declared observable schema and operator set",
    }


def legacy_observation_to_predicate(observation: Any) -> dict[str, Any] | None:
    """Convert the pre-contract marker used by preserved evidence."""
    if not isinstance(observation, dict):
        return None
    if "operator" in observation and "value" in observation:
        return {
            "path": observation.get("path"),
            "operator": observation.get("operator"),
            "value": observation.get("value"),
        }
    if "equals" in observation:
        return {"path": observation.get("path"), "operator": "equals", "value": observation.get("equals")}
    return None


def structured_failure_matches(experiment: Any, output: Any, predicate: Any) -> bool:
    checked = validate_structured_failure_predicate(predicate, experiment)
    if not checked.get("valid") or not isinstance(output, dict):
        return False
    normalized = checked["predicate"]
    if normalized is None:
        return False
    value: Any = output
    for part in normalized["path"]:
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return normalized["operator"] == "equals" and value == normalized["value"]
