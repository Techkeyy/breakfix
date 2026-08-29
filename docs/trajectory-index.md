# Trajectory and evidence index

All paths below are relative to the project directory unless marked as
external. Generated evidence is ignored by Git so provider responses and local
paths are not accidentally submitted with source.

| Run | Contents | Status |
| --- | --- | --- |
| `evidence/phase2b-20260829T190449Z/` | Preserved Phase 2B Attempt 1, 32 provider calls, fixed matrix, frozen ineligible FAIL | Historical development evidence |
| `evidence/provider-recovery-smoke-20260829T194240Z/` | Two authorized DeepSeek smoke trajectories with recovery telemetry | Engineering smoke PASS |
| `evidence/external-acceptance-20260829T201344Z/` | Independent non-benchmark acceptance, replay, regression, and reducer output | Acceptance PASS |
| `evidence/final-eval-20260829T212423Z/` | 16 baseline trajectories, 16 BreakFix trajectories, 128 fixed execution records, telemetry, and oracle-free final summary | Final primary gate PASS |

## Final run layout

- `trajectories/baseline/<case>/replay.json`: prompt hash, provider result,
  separated reasoning and final response, validation, and telemetry.
- `trajectories/breakfix/<case>/`: planner prompt, planner recovery, provider
  telemetry, selected experiments, isolated execution logs, and regression
  evidence.
- `fixed-matrix/<case>/<experiment>/`: command, payload, stdout, stderr, exit,
  timing, and parsed output from each deterministic execution.
- `final-summary.json`: metrics, gate, telemetry, case outcomes, and manifest
  hash with no evaluator truth path or expected-output fields.

The evaluator-only records containing expected outputs are retained outside
the repository in the Temp run directory and are not part of this published
index.
