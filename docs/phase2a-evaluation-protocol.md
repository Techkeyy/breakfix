# Phase 2A Evidence-Quality Evaluation Protocol

Status: frozen before the final Phase 2A benchmark run.

## Purpose and thesis

Phase 2A tests the narrow BreakFix thesis:

> Stop guessing what might break. Prove what actually does.

The product claim under test is evidence-backed precision plus targeted
efficiency. This protocol does not test whether BreakFix is more intelligent or
finds more defects than an ordinary coding agent.

## Primary metric: evidence-backed correct verdict rate

The primary metric is:

`correct verdicts / all holdout cases`

There are three allowed final verdicts: `DEFECT`, `SAFE`, and `INCONCLUSIVE`.

- A faulty case is correct only when the lane returns `DEFECT`.
- A safe case is correct only when the lane returns `SAFE`.
- `INCONCLUSIVE` is never a correct primary verdict. It is preserved and
  reported separately, rather than converted to `SAFE` or `DEFECT`.
- A baseline `DEFECT` is evidence-backed only when its finding cites observed
  source, test, or execution evidence. A baseline is not allowed to claim an
  observed hidden failure it did not run.
- For BreakFix, a `DEFECT` requires at least one deterministic supported
  experiment with actual execution evidence: command, setup/environment,
  expected versus actual result, stdout, stderr, exit/test status, and any
  artifact path. No execution means no confirmed break.

If an agent says “possible issue”, “likely”, or “needs review”, it must map that
uncertainty to `INCONCLUSIVE` unless it explicitly returns the required final
verdict. A possible issue is therefore not scored as a correct `SAFE` verdict.

## Deterministic BreakFix evidence states

The model proposes assumptions and supported experiment IDs. Deterministic
machinery validates the IDs, runs the experiment, and assigns the state.

- `CONFIRMED_BREAK`: the selected supported experiment has complete subprocess
  evidence and its actual result is a non-zero exit, timeout, or exact-output
  mismatch against the evaluator oracle.
- `CLEARED`: the selected supported experiment has complete subprocess evidence
  and its actual output exactly matches the frozen expected output.
- `INCONCLUSIVE`: an execution cannot establish the expected result, or the
  selected experiment has no frozen oracle for that case.
- `UNSUPPORTED`: the model proposed an experiment outside the supported
  catalogue, or the response/evidence is not valid enough to execute.

BreakFix's final verdict is deterministic:

- Any `CONFIRMED_BREAK` produces `DEFECT`.
- `SAFE` requires at least one selected experiment and every selected experiment
  to be `CLEARED`, with no `INCONCLUSIVE` or `UNSUPPORTED` item.
- Otherwise the final verdict is `INCONCLUSIVE`.

For a cleared retry assumption, the canonical wording is: “No duplicate effect
reproduced under tested retry scenario.” It must not be inflated to “Retry
logic is safe.” A cleared assumption is evidence for the tested scenario only.

## Secondary metrics

The evaluator reports these metrics for baseline, fixed matrix, and BreakFix
where applicable:

- fault recall: `faulty cases correctly returned as DEFECT / faulty cases`;
- safe-case specificity: `safe cases correctly returned as SAFE / safe cases`;
- false positives (FP): safe cases returned as `DEFECT`;
- false-positive rate (FAR): `FP / safe cases`;
- false approvals: faulty cases returned as `SAFE`;
- false-approval rate: `false approvals / faulty cases`;
- confirmed-failure rate: cases with at least one `CONFIRMED_BREAK` /
  faulty cases;
- executable reproduction rate: confirmed breaks with complete execution
  evidence / all confirmed breaks;
- total experiments executed;
- experiments per confirmed defect: total experiments / confirmed breaks;
- model calls, input tokens, output tokens, total tokens, latency, runtime, and
  monetary cost when supplied by the provider;
- execution runtime and evidence/trajectory paths.

`INCONCLUSIVE` is included in the denominator of correct verdict rate and
specificity, and is shown as its own count. It is never silently merged with
`SAFE`.

## Fixed comparison matrix and thresholds

The fixed matrix runs every supported experiment in the catalogue on every
holdout case. It does not select intelligently. BreakFix may select only from
the same catalogue, based on the change and its assumptions.

For the matrix lane, the case verdict is calculated from all oracle-backed
experiments: any confirmed break is `DEFECT`, and all oracle-backed experiments
clearing is `SAFE`. Non-oracled catalogue executions remain `UNSUPPORTED` in the
evidence bundle and do not turn an otherwise oracle-backed matrix verdict into
`INCONCLUSIVE`; they are still counted in matrix experiment volume.

The efficiency threshold is frozen before results:

1. BreakFix must execute no more than 50% of the fixed-matrix experiment count.
2. BreakFix must average no more than three experiments per confirmed defect.
3. BreakFix fault recall and safe-case specificity must each be no more than
   five percentage points below the matrix.

Phase 2A is a PASS only if BreakFix meets the matrix efficiency threshold and
shows at least one strong improvement over the live baseline: either at least
10 percentage points higher primary correct-verdict rate, or at least 50% fewer
false positives while losing no more than five percentage points of fault
recall. A result that is merely tied is reported as not proving improvement.

## Independent holdout composition

The final benchmark is `benchmark/phase2a_holdout/`, with 14 numeric cases:
seven faulty and seven safe. The previous five Phase 1.5 cases are development
cases and are excluded from the primary Phase 2A evidence.

The holdout is paired:

| Pair | Faulty | Safe | Target surface |
| --- | --- | --- | --- |
| 1 | h01 | h02 | retry/idempotency |
| 2 | h03 | h04 | empty input boundary |
| 3 | h05 | h06 | legacy persisted state |
| 4 | h07 | h08 | reordered events |
| 5 | h09 | h10 | timezone conversion |
| 6 | h11 | h12 | missing configuration |
| 7 | h13 | h14 | concurrent duplicate delivery |

Agents receive only a numeric case workspace containing `public.json`,
`before/app.py`, `after/app.py`, and visible tests. Ground truth is stored in a
separate evaluator-only file and is never included in prompts or workspaces.
The cases use ordinary task language and visible happy-path tests; filenames,
IDs, and task text do not label a fault.

## Provider and reproducibility lock

Baseline and BreakFix use the same direct provider, model, model settings, and
holdout context in a live run. The provider must expose model ID, input/output
tokens, latency, and cost, or expose enough information to calculate cost using
the committed per-token rates. Secrets are environment-only and `.env.example`
contains names but no values.

The repository includes an OpenAI-compatible direct provider path. If that path
cannot authenticate, a replay run may preserve engineering artifacts but is not
treated as a direct-provider PASS. The evaluator reports unavailable telemetry
as `null`; it never invents tokens or cost.

## Integrity rules

- The evaluator may read ground truth; agents may not.
- The evaluator must use real subprocess execution for every selected and matrix
  experiment.
- Every confirmed break must have the complete execution evidence bundle.
- The baseline and BreakFix prompts, model metadata, and settings are committed.
- The fixed matrix is fresh on this holdout and is not copied from Phase 1.5.
- No result is upgraded because a source-level suspicion sounds plausible.

## Stop condition

After the Phase 2A run, report the frozen protocol commit, run commit, provider
metadata, case-level results, confusion matrices, all metrics above, evidence
paths, cleared and confirmed examples, inconclusive/unsupported items, the
comparison to Phase 1.5, revised-thesis status, efficiency status, biggest
risk, and the exact Phase 2B scope. Do not start polished frontend, GitHub/CI,
large sandboxing, reducers, fixes, multilingual support, or an extensive report
until this gate is decided.
