# BreakFix final form answers

Prepared for copy and adaptation to the official submission form. The video URL
stays a placeholder until the recording is uploaded.

## PROJECT NAME

BreakFix

## ONE-LINER

Stop guessing what might break. Prove what actually does.

## PROBLEM

Coding agents and existing tests can identify plausible risks, but a warning is
still only a hypothesis. The assumptions introduced by a change often fail on
empty input, old state, retries, event order, timing, or configuration paths
that the visible suite does not exercise.

## TARGET USER

Developers and coding agents responsible for reviewing a real code change.

## SOLUTION

BreakFix reads a selected change, makes its behavioral assumptions explicit,
selects a small set of high-value supported experiments, executes them in
isolation, and preserves the evidence needed to reproduce a real break.

## HOW THE AGENT WORKS

The agent receives the public repository change, task, and visible tests. It
returns ranked assumptions and one supported experiment per assumption. The
deterministic engine executes the selected probes, captures expected and actual
behavior, and produces the verdict. The model does not decide whether a break
is real.

## WHY AN AGENT IS NECESSARY

The difficult part is translating an open-ended code diff into a short list of
specific, falsifiable assumptions worth executing. A fixed test matrix spends
the same effort everywhere. BreakFix uses agent reasoning to choose where to
spend bounded execution while keeping the decision evidence-based.

## BASELINE

The same-model generic comparator receives the same public change and visible
tests, but has no hidden probe catalogue and does not execute the probes. On the
frozen holdout it recalled 7 of 8 seeded faults with zero safe false confirmed
breaks.

## PRIMARY METRIC

Total targeted experiments needed for complete seeded-fault recall with zero
false confirmed breaks on the frozen holdout.

## FINAL RESULTS

BreakFix confirmed 8 of 8 seeded faults and 0 of 8 safe false confirmed breaks.
It executed 38 targeted experiments versus 128 in the fixed matrix.

## MEASURED IMPROVEMENT

On the frozen final holdout, BreakFix found all 8 seeded faults with zero false
confirmed breaks while executing 38 targeted experiments instead of the fixed
matrix's 128, a 70.3% reduction.

## IMPROVEMENT CHANGELOG SUMMARY

- A strong coding agent already found the raw faults, but that did not prove
  they were real.
- A broad safety-certification framing failed its frozen quality gate.
- Phase 2B Attempt 1 failed because a 2,000-token adapter truncated advanced
  planner outputs; the failure was preserved.
- Provider recovery changed the output contract and evidence handling without
  changing the frozen cases, prompts, thresholds, oracle, budget, or gate.
- The final thesis became targeted, evidence-efficient falsification, and the
  final independent holdout passed.

## REPRODUCIBILITY

Source: https://github.com/Techkeyy/breakfix

Run the clean-environment instructions in `REPRODUCE.md`. The repository
contains the oracle-free final evidence, trajectories, telemetry, fixed
executions, canonical demo evidence, and improvement changelog. The evaluator
truth remains external.

## HUMAN APPROVAL / SAFETY

Candidate fixes are proposed but never applied without an explicit human
approval action. The approved candidate is applied and verified in an isolated
snapshot. BreakFix does not merge, push, or write back to the source repository.
Hosted jobs accept public repositories only and run within bounded resource and
time limits. Provider credentials remain outside submitted source.

## TECH STACK

Python standard library, subprocess execution, sanitized temporary workspaces,
Docker isolation, a thin static HTML/CSS/JavaScript frontend, Vercel hosting,
and a public HTTPS API.

## MODEL / PROVIDER

DeepSeek V4 Pro with high reasoning effort, JSON object mode, a 12,000-token
completion budget, bounded retries, structured-output recovery, and recorded
telemetry. The final evaluation used 32 live model calls.

## GITHUB URL

https://github.com/Techkeyy/breakfix

## LIVE URL

https://breakfix.vercel.app

## VIDEO URL

PENDING UPLOAD

## TRAJECTORY LOCATION

Public oracle-free final evidence:
`submission/evidence/final-eval-20260829T212423Z/`

Historical Attempt 1 and recovery evidence are indexed in
`docs/trajectory-index.md`.

## LIMITATIONS

The supported MVP expects a Python project exposing `app.run(payload)` and a
runnable unittest command. It supports four experiment surfaces: input, state,
timing, and world. Hosted jobs accept public repositories only, run one active
job at a time, and have no multi-user authentication. The 16-case holdout does
not establish general defect-detection accuracy or support for arbitrary
languages.

## HOT TAKE

As coding agents get better at imagining possible failures, generating more
suspicions stops being the hard part. The bottleneck becomes deciding which
suspicions are worth executing and proving which failures are real.
