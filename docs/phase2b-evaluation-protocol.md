# Phase 2B Evaluation Protocol

Status: frozen before the Phase 2B benchmark.

## 1. Scope and claim

Phase 2B is the last thesis-validation gate for the narrow BreakFix claim:

> BreakFix is an evidence-efficient break confirmation engine.

The claim under test is that BreakFix can infer which change-specific
assumptions are worth attacking, execute only a bounded set of supported
attacks, and produce reproducible proof when a real failure exists.

Phase 2B does not test universal safety, certification, raw bug-hypothesis
generation, UI, GitHub integration, CI, automatic fixes, regression
generation, reducers, additional languages, or additional break surfaces.

## 2. Outcome vocabulary

BreakFix overall outcomes are deterministic and are not safety certification:

- `CONFIRMED BREAK`: a selected supported experiment executed and established a
  real mismatch or failure with complete evidence.
- `NO BREAK CONFIRMED`: selected supported experiments executed and cleared; no
  failure was reproduced under the tested scenarios. This is not a universal
  safety guarantee.
- `UNSUPPORTED`: no usable supported experiment could test the relevant
  assumption, or the response proposed only unsupported machinery. The report
  may include `UNSUPPORTED ASSUMPTIONS` alongside `NO BREAK CONFIRMED` when
  supported selected experiments cleared.
- `ERROR`: the evaluation could not complete because of a provider, tool, or
  runtime failure rather than an application behavior established by an oracle.

At the individual-assumption level, the only positive wording is
`CLEARED UNDER TESTED SCENARIO`. No result may claim that a change is
universally safe.

## 3. Primary metric

The single frozen primary metric is:

> Total executable experiments required for BreakFix to reach complete seeded-
> fault recall while producing zero false `CONFIRMED BREAK` outcomes.

The eligible set is eight faulty and eight safe cases. Therefore:

- complete seeded-fault recall means `8 / 8 = 100%` faulty cases end as
  `CONFIRMED BREAK`;
- zero false confirmed breaks means `0 / 8 = 0%` safe cases end as
  `CONFIRMED BREAK`;
- the primary value is the total number of BreakFix experiments executed across
  all 16 cases when both conditions hold;
- if either condition fails, the primary result is `NOT ACHIEVED`, while the
  observed experiment count and all secondary metrics remain reported.

This definition is mathematically explicit for the 8-fault sample. It avoids
pretending that a fractional 95% threshold has more resolution than the
holdout: for eight faults, a threshold of at least 95% also requires 8/8.

## 4. Frozen pass thresholds

Phase 2B can PASS only if every condition below holds:

1. BreakFix reaches the primary eligibility condition: `8/8` seeded-fault
   recall and `0/8` false confirmed breaks.
2. BreakFix executes at least 50% fewer experiments than the fixed matrix,
   meaning no more than `64` experiments when the fixed matrix executes
   `16 * 8 = 128`.
3. Every confirmed break has complete executable evidence.
4. Direct provider telemetry is present for model, input tokens, output
   tokens, latency, approximate cost, retries, and API errors.
5. The independent leakage audit finds no answer-revealing leakage.
6. The run has no lane-level tool/runtime failure that invalidates comparison.

The generic coding-agent lane is a secondary comparator and need not beat
BreakFix for a PASS. The fixed exhaustive matrix is the primary baseline.

## 5. Deterministic BreakFix budget and stop policy

The policy is fixed before execution and is the same for every case:

1. The agent inspects only the public case workspace and visible tests.
2. It emits assumptions ranked from highest to lowest expected falsification
   value, with one proposed catalogue experiment per assumption.
3. The validator removes duplicate supported IDs while preserving ranked order.
   IDs outside the supported catalogue are recorded as unsupported and are not
   executable.
4. The executor runs at most `K = 3` supported experiments per case.
5. After each execution, deterministic evaluator machinery assigns the evidence
   state. If a `CONFIRMED_BREAK` is established, execution stops immediately
   for that case.
6. If no break is confirmed, the executor stops after the third supported
   experiment, when no supported experiment remains, or when the agent proposed
   no supported experiment.
7. A case with at least one selected supported experiment and all selected
   oracle-backed executions cleared becomes `NO BREAK CONFIRMED`, even if the
   agent also recorded unrelated unsupported assumptions. Those assumptions
   remain visible as `UNSUPPORTED ASSUMPTIONS`.
8. A case with no executable supported experiment becomes `UNSUPPORTED`.

The model never decides that it has tested enough after observing a result.
Budget, ordering, deduplication, break stopping, and final outcome are
deterministic evaluator behavior.

## 6. Fixed exhaustive matrix policy

The primary baseline runs all eight supported catalogue experiments on every
case, exactly once, for 128 experiment executions. It performs no agentic
selection and uses the same deterministic evidence-state evaluator.

The catalogue is unchanged from Phase 2A:

`input_empty`, `input_boundary_zero`, `retry_duplicate`, `state_legacy`,
`events_reordered`, `world_dst`, `config_missing`, and `concurrent_duplicate`.

## 7. Three lanes and prompts

All lanes use the same fresh holdout and direct provider, model, settings, and
public context where applicable:

- Lane A: generic coding-agent review, a secondary reasoning-only comparator.
- Lane B: fixed exhaustive perturbation matrix, the primary baseline.
- Lane C: BreakFix targeted selection plus deterministic execution.

Exact prompt templates are frozen in `docs/phase2b-prompts.md` before the run.
The generic lane may report a suspected defect from source, visible tests, or
its own reasoning, but may not claim hidden execution it did not perform.
BreakFix may rank and select; only deterministic execution can establish a
confirmed break.

## 8. Direct provider and telemetry

Phase 2B agent lanes use a real authenticated OpenAI-compatible provider path.
The provider records model ID, input tokens, output tokens, total tokens,
request latency, retry count, API errors, and approximate USD cost calculated
from environment-provided per-1K-token rates. Both agent lanes use the same
provider, model, temperature, reasoning setting, and output limit.

Secrets are environment-only. `.env.example` contains variable names and no
credentials. A run without an authenticated direct provider is a preflight
failure, not Phase 2B evidence and not a PASS.

## 9. Fresh independent holdout

The final holdout is `benchmark/phase2b_holdout/` with 16 numeric cases:
eight mechanically faulty changes and eight clean controls arranged as eight
new pairs. It covers each currently supported surface without adding a new
surface. No Phase 1, Phase 1.5, or Phase 2A case is reused as final evidence.

Ground truth is stored in `benchmark/phase2b_ground_truth.json`, readable only
by the evaluator. It is absent from the public workspaces, prompts, planner,
runtime environment, trajectories, and agent responses.

## 10. Leakage audit and evidence integrity

Before execution, `docs/phase2b-leakage-audit.md` records inspection of case
filenames, test names, comments, commit messages, task text, directory names,
fixture metadata, source constants, and prompt context for fault labels,
expected breakers, safe/faulty labels, and oracle data. The audit reviewer is
separate from the planner/evaluator workflow and does not modify results after
execution begins.

Every confirmed break stores command/setup, expected and actual behavior,
stdout, stderr, exit/test status, and an evidence path. The report must not
upgrade a source suspicion into a confirmed break without execution.

## 11. Required report and stop rule

After the Phase 2B run, report PASS/MIXED/FAIL, BUILD/NARROW/PIVOT, both
commits, provider and settings, holdout composition and leakage result,
budget/matrix policies, exact prompts, primary metric and thresholds, all lane
metrics, experiments and reduction, experiments per confirmed defect, runtime,
tokens, cost, latency, retries/errors, evidence and trajectory paths,
unsupported assumptions, no-break-confirmed rate, confirmed-break evidence and
reproduction rates, a case table, comparison to Phase 2A, thesis status,
biggest risk, and the exact Phase 3 recommendation if PASS.

Stop after this report. Any further work requires a new director decision.
