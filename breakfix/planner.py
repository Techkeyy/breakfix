from __future__ import annotations

from .experiments import experiment_by_id
from .models import Assumption


def infer_assumptions(diff: str) -> list[Assumption]:
    added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    text = f"{added}\n{removed}\n{diff}".lower()
    assumptions: list[Assumption] = []

    if any(signal in text for signal in ("/ len(", "max(", "min(")) or "payload[\"items\"]" in text:
        assumptions.append(
            Assumption(
                id="input-shape",
                surface="input",
                statement="The changed path still receives a non-empty, well-shaped input.",
                evidence=["The diff introduces direct input access or an operation with a boundary case."],
                risk=0.86,
                selected_experiments=["input_empty", "input_boundary_zero"],
            )
        )

    if any(signal in text for signal in ("attempts", "_processed", "charge", "idempot")):
        assumptions.append(
            Assumption(
                id="operation-idempotency",
                surface="timing",
                statement="A repeated delivery of the same operation cannot apply its side effect twice.",
                evidence=["The diff changes retry or duplicate-operation handling."],
                risk=0.91,
                selected_experiments=["retry_duplicate"],
            )
        )

    if "state[" in text or (".get(" in text and "state" in text):
        assumptions.append(
            Assumption(
                id="persisted-state-shape",
                surface="state",
                statement="Persisted state always contains the newly accessed field.",
                evidence=["The diff changes how a field is read from persisted state."],
                risk=0.88,
                selected_experiments=["state_legacy"],
            )
        )

    if all(signal in text for signal in ("events", "reserve", "confirm")):
        assumptions.append(
            Assumption(
                id="event-order",
                surface="timing",
                statement="Valid events arrive in the same order as the happy-path test.",
                evidence=["The diff processes a multi-step event sequence."],
                risk=0.79,
                selected_experiments=["events_reordered"],
            )
        )

    if any(signal in text for signal in ("datetime", "timezone", "zoneinfo", "fromisoformat")):
        assumptions.append(
            Assumption(
                id="clock-and-world",
                surface="world",
                statement="The changed time calculation remains correct across timezone boundaries.",
                evidence=["The diff changes timestamp or timezone interpretation."],
                risk=0.63,
                selected_experiments=["world_dst"],
            )
        )

    return sorted(assumptions, key=lambda item: item.risk, reverse=True)


def targeted_experiments(assumptions: list[Assumption]) -> list[str]:
    selected: list[str] = []
    for assumption in assumptions:
        for experiment_id in assumption.selected_experiments:
            experiment_by_id(experiment_id)
            if experiment_id not in selected:
                selected.append(experiment_id)
    return selected
