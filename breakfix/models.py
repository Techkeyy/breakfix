from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Experiment:
    id: str
    surface: str
    description: str
    perturbation: dict[str, Any]


@dataclass(frozen=True)
class Assumption:
    id: str
    surface: str
    statement: str
    evidence: list[str]
    risk: float
    selected_experiments: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    experiment_id: str
    command: list[str]
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    output: Any = None
    duration_ms: int = 0

    @property
    def process_failed(self) -> bool:
        return self.timed_out or self.exit_code != 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "command": self.command,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output": self.output,
            "duration_ms": self.duration_ms,
            "process_failed": self.process_failed,
        }
