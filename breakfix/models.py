from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Experiment:
    id: str
    surface: str
    description: str
    perturbation: dict[str, Any]
    target: str = ""
    observable: str = ""
    failure_predicate: str = ""
    capability: str = "python-runtime"
    match_terms: tuple[str, ...] = ()


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
    output_captured: bool = False
    duration_ms: int = 0

    @property
    def process_failed(self) -> bool:
        return self.timed_out or self.exit_code != 0

    @property
    def failure_kind(self) -> str:
        """Classify a failed subprocess conservatively.

        A non-zero exit is not enough to establish a target failure. Missing
        modules, launch errors, timeouts, and diagnostics without a target
        exception remain harness failures.
        """
        if not self.process_failed:
            return "TARGET_SUCCESS"
        if self.timed_out:
            return "HARNESS_FAILURE"
        diagnostic = f"{self.stdout}\n{self.stderr}".lower()
        harness_markers = (
            "modulenotfounderror",
            "importerror",
            "no module named",
            "can't open file",
            "cannot open file",
            "no such file or directory",
            "command not found",
            "permission denied",
            "pip install",
        )
        target_markers = (
            "traceback",
            "assertionerror",
            "valueerror",
            "keyerror",
            "zerodivisionerror",
            "typeerror",
            "indexerror",
            "runtimeerror",
            "overflowerror",
        )
        if any(marker in diagnostic for marker in harness_markers):
            return "HARNESS_FAILURE"
        if any(marker in diagnostic for marker in target_markers):
            return "TARGET_FAILURE"
        return "HARNESS_FAILURE"

    @property
    def target_failed(self) -> bool:
        return self.failure_kind == "TARGET_FAILURE"

    @property
    def harness_failed(self) -> bool:
        return self.failure_kind == "HARNESS_FAILURE"

    @property
    def concrete_observable(self) -> bool:
        if self.output_captured:
            return True
        return self.target_failed and bool(self.stdout.strip() or self.stderr.strip()) and self.exit_code is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "command": self.command,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output": self.output,
            "output_captured": self.output_captured,
            "duration_ms": self.duration_ms,
            "process_failed": self.process_failed,
            "failure_kind": self.failure_kind,
            "target_failed": self.target_failed,
            "harness_failed": self.harness_failed,
            "concrete_observable": self.concrete_observable,
        }
