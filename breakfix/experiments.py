from __future__ import annotations

from copy import deepcopy
from typing import Any

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
}


EXPERIMENTS: tuple[Experiment, ...] = (
    Experiment(
        id="input_empty",
        surface="input",
        description="Send an empty collection where the change may assume an item exists.",
        perturbation={"items": []},
    ),
    Experiment(
        id="input_boundary_zero",
        surface="input",
        description="Send the smallest numeric collection with a zero value.",
        perturbation={"items": [0]},
    ),
    Experiment(
        id="retry_duplicate",
        surface="timing",
        description="Replay the same request twice to challenge idempotency.",
        perturbation={"attempts": 2},
    ),
    Experiment(
        id="state_legacy",
        surface="state",
        description="Load an older persisted record that lacks a newly assumed field.",
        perturbation={"state": {"version": 1, "balance": 100}},
    ),
    Experiment(
        id="events_reordered",
        surface="timing",
        description="Deliver a valid event sequence in a different order.",
        perturbation={"events": ["confirm", "reserve"]},
    ),
    Experiment(
        id="world_dst",
        surface="world",
        description="Evaluate a UTC instant across a daylight-saving timezone boundary.",
        perturbation={
            "timestamp": "2026-03-29T20:30:00+00:00",
            "timezone": "America/New_York",
        },
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
