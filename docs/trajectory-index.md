# Trajectory and evidence index

All paths below are relative to the project directory unless marked as
external. Development evidence is ignored by Git; the curated copies needed
for submission are tracked under `submission/evidence/`.

| Run | Contents | Status |
| --- | --- | --- |
| `evidence/phase2b-20260829T190449Z/` | Preserved Phase 2B Attempt 1, 32 provider calls, fixed matrix, frozen ineligible FAIL | Historical development evidence |
| `evidence/provider-recovery-smoke-20260829T194240Z/` | Two authorized DeepSeek smoke trajectories with recovery telemetry | Engineering smoke PASS |
| `evidence/external-acceptance-20260829T201344Z/` | Independent non-benchmark acceptance, replay, regression, and reducer output | Acceptance PASS |
| `evidence/final-eval-20260829T212423Z/` | 16 baseline trajectories, 16 BreakFix trajectories, 128 fixed execution records, telemetry, and oracle-free final summary | Final primary gate PASS |

| evidence/canonical-demo-20260829T223714Z/ | Full non-benchmark break, replay, regression, proposed fix, explicit approval, application, and verification journey | Demo VERIFIED |

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

## Representative trajectories for judges

| Representative | Purpose | Agent instructions and input/context | Important tool calls and outputs | Retries/failures | Human checkpoint | Final result | Artifact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BreakFix planner | Analyze the selected change and rank falsifiable assumptions | Product planner prompt; public q1a change, visible tests, and supported catalogue | Provider call, schema validation, assumption ranking, selected `input_empty`, isolated execution | Provider telemetry and recovery record; no hidden oracle in context | None before analysis | `CONFIRMED BREAK` with regression evidence | `evidence/final-eval-20260829T212423Z/trajectories/breakfix/q1a/` |
| Generic baseline | Review the same public change without hidden probes | Generic comparator prompt; same q1a public change and visible tests | Provider call, JSON validation, separated reasoning/final output | Retries and finish reason are preserved in replay metadata | None; reasoning only | Structured recommendation, scored as the secondary baseline | `evidence/final-eval-20260829T212423Z/trajectories/baseline/q1a/` |
| Provider recovery | Preserve a response-contract failure and bounded recovery behavior | Historical Phase 2B Attempt 1 and two authorized smoke controls | Truncated response, explicit provider-output error, recovered JSON response, telemetry | Attempt 1 failed at the 2,000-token ceiling; one bounded recovery path is recorded | Authorization was required for the smoke calls | Historical FAIL preserved; smoke PASS | `evidence/phase2b-20260829T190449Z/` and `evidence/provider-recovery-smoke-20260829T194240Z/` |
| Confirmed break | Show deterministic evidence rather than model assertion | Canonical independent sample, selected change, visible tests, and `input_empty` payload | Visible tests, planner, isolated subprocess, replay, regression generation, reducer | No provider failure; execution process failure is recorded | None before evidence capture | Reproduced break and valid regression | `evidence/canonical-demo-20260829T223714Z/` |
| Approval and verification | Show the human checkpoint before a consequential patch | Candidate patch generated from the canonical confirmed-break evidence | Proposal, explicit approval, application, after-fix replay, visible tests | Approval is required; no merge or push | Human approval recorded as `approved=true` | `VERIFIED`; regression and original tests pass | `evidence/canonical-demo-20260829T223714Z/fix/` |

The trajectories preserve visible prompts, tool inputs and outputs, retries,
validation, and final results without exposing chain-of-thought, credentials,
or evaluator truth.

## Curated submission copy

The portable package copies the final public bundle, canonical demo, historical
Phase 2B Attempt 1 result, provider-recovery smoke, and independent acceptance
evidence under `submission/evidence/`. The copied final and Phase 2B evidence is
oracle-free. The evaluator-only truth remains in the external Temp run
workspace and is not copied.
