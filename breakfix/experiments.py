from __future__ import annotations

from copy import deepcopy
from typing import Any

from .evidence_contract import legacy_observation_to_predicate, structured_failure_matches
from .models import Experiment


BASE_CONTEXT: dict[str, Any] = {
    "items": [10, 20, 30],
    "request_id": "charge-001",
    "amount": 25,
    "attempts": 1,
    "state": {"version": 2, "tax_rate": 0.2},
    "events": ["reserve", "confirm"],
    "timestamp": "2026-01-15T19:00:00+00:00",
    "timezone": "America/New_York",
    "config": {"currency": "USD"},
    "concurrent_calls": 1,
}


def _object_schema(properties: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "additionalProperties": False}


INPUT_OUTPUT_SCHEMA = _object_schema({
    "average": {"type": ["number", "null"]},
    "count": {"type": "integer"},
    "source": {"type": "string"},
    "value": {"type": "number"},
    "reading": {"type": ["number", "null"]},
    "present": {"type": "boolean"},
})
RETRY_OUTPUT_SCHEMA = _object_schema({
    "accepted": {"type": "boolean"},
    "attempts": {"type": "integer"},
    "replays": {"type": "integer"},
    "status": {"type": "string"},
})
STATE_OUTPUT_SCHEMA = _object_schema({
    "tax": {"type": "number"},
    "version": {"type": "integer"},
})
EVENT_OUTPUT_SCHEMA = _object_schema({
    "event_count": {"type": "integer"},
    "sequence": {"type": "string"},
})
WORLD_OUTPUT_SCHEMA = _object_schema({
    "offset_mode": {"type": "string"},
    "zone": {"type": "string"},
    "calendar": {"type": "string"},
})
CONFIG_OUTPUT_SCHEMA = _object_schema({
    "mode": {"type": "string"},
    "region": {"type": "string"},
})


EXPERIMENTS: tuple[Experiment, ...] = (
    Experiment(
        id="input_empty",
        surface="input",
        description="Send an empty collection where the change may assume an item exists.",
        perturbation={"items": []},
        target="input collection boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target raises when the input collection is empty",
        match_terms=("empty", "non-empty", "collection", "item", "length", "list", "array", "input"),
        observable_schema=INPUT_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="input_boundary_zero",
        surface="input",
        description="Send the smallest numeric collection with a zero value.",
        perturbation={"items": [0]},
        target="numeric input boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target fails or returns an invalid result for a zero-valued boundary",
        match_terms=("zero", "numeric", "number", "boundary", "value", "input"),
        observable_schema=INPUT_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="retry_duplicate",
        surface="timing",
        description="Replay the same request twice to challenge idempotency.",
        perturbation={"attempts": 2},
        target="request handling and side-effect boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target applies a repeated request more than once or fails on replay",
        match_terms=("retry", "replay", "duplicate", "idempot", "request", "attempt"),
        observable_schema=RETRY_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="state_legacy",
        surface="state",
        description="Load an older persisted record that lacks a newly assumed field.",
        perturbation={"state": {"version": 1, "balance": 100}},
        target="persisted state schema boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target fails when a legacy record lacks the newly assumed field",
        match_terms=("legacy", "older", "old", "persisted", "schema", "field", "record", "state", "backward"),
        observable_schema=STATE_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="events_reordered",
        surface="timing",
        description="Deliver a valid event sequence in a different order.",
        perturbation={"events": ["confirm", "reserve"]},
        target="event sequencing boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target produces an invalid transition or fails for a reordered event sequence",
        match_terms=("event", "order", "ordered", "sequence", "transition", "out-of-order", "reorder"),
        output_failure_observation={"path": ["sequence"], "operator": "equals", "value": "invalid"},
        observable_schema=EVENT_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="world_dst",
        surface="world",
        description="Evaluate a UTC instant across a daylight-saving timezone boundary.",
        perturbation={
            "timestamp": "2026-03-29T20:30:00+00:00",
            "timezone": "America/New_York",
        },
        target="timestamp and timezone boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target computes a wrong or failed result across a daylight-saving boundary",
        match_terms=("timezone", "time zone", "daylight", "dst", "utc", "timestamp", "calendar", "locale"),
        observable_schema=WORLD_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="config_missing",
        surface="state",
        description="Remove an optional configuration field to test the dependency boundary.",
        perturbation={"config": {}},
        target="optional configuration boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target fails when optional configuration is absent",
        match_terms=("config", "configuration", "setting", "optional", "dependency", "missing"),
        observable_schema=CONFIG_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
    Experiment(
        id="concurrent_duplicate",
        surface="timing",
        description="Deliver two concurrent copies of one request through the effect boundary.",
        perturbation={"concurrent_calls": 2},
        target="concurrent effect boundary",
        observable="structured return or captured target exception",
        failure_predicate="the target races, duplicates a side effect, or fails under concurrent delivery",
        match_terms=("concurrent", "concurrency", "parallel", "race", "simultaneous", "effect boundary"),
        observable_schema=RETRY_OUTPUT_SCHEMA,
        allowed_predicate_operators=("equals",),
    ),
)


def experiment_by_id(experiment_id: str) -> Experiment:
    for experiment in EXPERIMENTS:
        if experiment.id == experiment_id:
            return experiment
    raise KeyError(f"Unknown experiment: {experiment_id}")


def payload_for(experiment: Experiment) -> dict[str, Any]:
    payload = deepcopy(BASE_CONTEXT)
    payload.update(deepcopy(experiment.perturbation))
    return payload


_DEFAULT_PREDICATE = object()


def output_failure_matches(experiment: Experiment, output: Any, predicate: Any = _DEFAULT_PREDICATE) -> bool:
    """Evaluate an exact, schema-validated structured failure predicate."""
    if predicate is _DEFAULT_PREDICATE:
        predicate = legacy_observation_to_predicate(experiment.output_failure_observation)
    return structured_failure_matches(experiment, output, predicate)
