# BreakFix Phase 1 exit report

Date: 2026-08-29

Status: prototype mechanism PASS; official completeness gate FAIL.

This is the deliberate Phase 0 and Phase 1 stopping point. The core comparison
works on a small reproducible benchmark, but the baseline is an offline
deterministic surrogate rather than a live coding-agent run. That gap means the
hackathon's required baseline comparison is not yet honestly complete.

## Project and evidence

- Canonical project: `C:\\Users\\HomePC\\Desktop\\BreakFix`
- Final run: `evidence/phase1-20260829T104633Z/`
- Comparison record: `evidence/phase1-20260829T104633Z/comparison.json`
- Replay command: `python scripts/run_phase1.py`
- Unit command: `python -m unittest discover -s tests -v`
- Final unit result: 8 passing tests in 1.462 seconds
- Final runner result: five visible case suites passed
- Git checkpoint: reported with the final handoff after the clean commit

The evidence bundle contains captured subprocess stdout, stderr, exit status,
output mismatch information, per-experiment duration, and trajectory records.
The runner really invokes each case in a subprocess. It does not pretend that a
model call or a sandbox exists. No model/API cost was incurred. Total runner
wall-clock time was not separately captured; per-experiment duration is stored
in each execution result.

## Requirements and skill audit

The official source consulted was the [micro1 Frontier Engineering Challenge
2026 page](https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/).
It confirms the individual online format, required coding-agent use, baseline
plus advanced solution comparison, reproducibility, measured improvement, and
agent trajectories. The linked instruction PDF was discovered but could not be
retrieved in this environment, so its exact contents and exact scoring weights
remain UNKNOWN. This is recorded in `docs/hackathon-requirements.md` rather
than inferred.

The required local skill material was read and applied:

- `audit-skill`: claims are separated from observed evidence and the final
  limitations are explicit.
- `build-process`: the risky comparison was built before UI work; deterministic
  execution, tests, four-state outcomes, and reproducible commands were used.
- `perfect-readme`: the README reports raw counts, commands, scope, and missing
  capabilities without phantom claims.
- `design-skill`: UI work was intentionally deferred because Phase 1 is a
  workflow and evidence checkpoint, not a polished product surface.
- `project-understanding`: the product sentence, journey, magic moment, data,
  trust boundary, load-bearing hypothesis, MVP, and non-goals are documented.
- `project-edge`: adjacent categories and the specific change-aware wedge are
  documented in `docs/project-edge.md`.
- `hackathon-onboarding`: requirements, environment limits, credentials, and
  reproducibility risks are documented.

## What was built

BreakFix takes a before/after `app.py` change and visible tests, infers changed
assumptions, selects targeted experiments, executes them against the changed
code, and stores evidence. The fixed comparison lane runs the same six
experiments for every case. The baseline lane performs only a generic offline
review of the diff and visible test result.

The six deterministic experiments are:

1. empty input
2. boundary-zero input
3. duplicate retry
4. legacy persisted state
5. reordered reserve/confirm events
6. daylight-saving/timezone world state

The controlled contract is intentionally narrow: a local Python module with
`run(payload)`. There is no GitHub integration, live model, arbitrary-repository
container, reducer, regression test generation, fix application, approval
flow, or UI in this checkpoint.

## Five-case result

| Case | Ground-truth fault | Baseline | Fixed matrix | BreakFix targeted result |
| --- | --- | --- | --- | --- |
| Input boundary | Empty list crashes | Detected | Detected, 6 runs | Detected, 2 runs |
| Retry duplicate | Retry charges twice | False approval | Detected, 6 runs | Detected, 1 run |
| Stale state | Legacy state crashes | Detected | Detected, 6 runs | Detected, 1 run |
| Reordered events | Confirm-before-reserve remains pending | False approval | Detected, 6 runs | Detected, 1 run |
| Timezone robust | No fault | No finding | No confirmed break | No confirmed break, 1 run |

Aggregate metrics from the final comparison record:

- Fault cases: 4. Safe cases: 1.
- Baseline surrogate: 2/4 fault detection, 50% false-approval rate, 0 false
  positives, 0 experiments.
- Fixed matrix: 4/4 fault detection, 30 experiments.
- BreakFix targeted planner: 4/4 fault detection, 6 experiments, no confirmed
  break on the safe timezone case.
- Integrity flags: real subprocess executions true, live model used false,
  evaluator-only ground truth true, offline surrogate true.

The final run missed no seeded fault among these five cases. An earlier planner
revision missed the reordered-events fault because its heuristic only noticed
changed event lines. The diff context was corrected, and the final run detected
the case. That repair is recorded in `docs/improvement-changelog.md`.

## Hypothesis decision

Hypothesis: change-aware assumption falsification finds more meaningful defects
than a generic review or a fixed checklist while spending fewer experiments.

Decision: provisionally supported by the deterministic benchmark, not yet
validated as a hackathon-ready agent claim. BreakFix matched the fixed matrix's
4/4 seeded fault detection with 6 experiments instead of 30, while preserving
the safe case. The comparison is not conclusive because the generic lane is not
a real coding agent, the benchmark is synthetic and small, and the cases are
designed around the current supported surfaces.

## Recommended architecture after Phase 1

Keep the evidence core deterministic and make model behavior observable around
it:

1. ingest a repo snapshot, change, tests, and explicit execution policy;
2. produce a versioned assumption graph from diff and repository context;
3. have the agent propose experiments with rationale, risk, and stop rules;
4. execute only approved experiments in a real isolated sandbox;
5. classify process failures, output mismatches, and harmless variation;
6. reduce confirmed failures into regression tests;
7. require human approval before any fix or consequential action;
8. retain all instructions, tool calls, outputs, retries, and checkpoints.

The model should propose and explain. The evidence layer should decide what
actually happened.

## Risks, removals, and divergence

Removed or deferred from this checkpoint: polished dashboard UI, broad GitHub
workflow, arbitrary third-party code execution, live model integration, reducer,
regression generation, automatic fixes, and submission video. These were
deferred because they would obscure whether the central comparison works.

Current risks are sandbox security, benchmark overfitting, incomplete official
PDF requirements, lack of a live comparable baseline, synthetic-case bias,
ambiguous classification of nondeterministic outputs, and an unverified cost
model. The local executor is a development harness, not a production sandbox.

The implementation therefore diverges from the full requested end state in one
material way: it does not yet provide a real live-agent baseline and advanced
workflow comparison. It also has not completed the later submission artifacts
such as the <=5 minute video. Those are open work, not hidden claims.

## Next phase gate

Do not start UI polish yet. Phase 2 should first wire one real baseline model and
one real BreakFix agent path under the same repo, change, tests, timeout, and
execution policy. Then expand the benchmark beyond five cases, freeze evaluator
truth separately from agent context, measure runtime and model cost, and rerun
the same comparison. If that gate holds, build reducer/regression evidence and
the approval flow before the UI.

Phase 1 stops here with a reproducible, inspectable prototype and an explicit
FAIL on the missing live-agent completeness requirement.
