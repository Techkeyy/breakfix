# Final independent evaluation protocol

Status: **frozen before final evaluation**  
Freeze date: 2026-08-29  
Product checkpoint: `13b8c89`
Public holdout checkpoint: `4939d76`

## Purpose

This is the final independent evaluation of the current BreakFix product. The
Phase 2B Attempt 1 cases are development evidence and are excluded. A fresh
opaque holdout is evaluated without changing the product, prompts, thresholds,
budget, or scoring after cases are generated.

## Holdout

- 16 opaque cases: 8 faulty changes and 8 non-faulty controls.
- Four supported surfaces are represented: input, state, timing, and world.
- Each case contains only public task text, before/after source, and visible
  tests. Fault labels and expected outputs live in an external evaluator-only
  truth file.
- The agent-visible workspace contains no oracle file, answer-bearing fixture
  metadata, revealing case names, or fault labels.

## Lanes

All three lanes use the exact same selected change, public context, visible test
command, and final holdout:

1. Generic DeepSeek comparator: reasoning-only recommendation, no hidden probes.
2. Fixed exhaustive matrix: all eight deterministic supported experiments per
   case, evaluator-only expected-output comparison.
3. BreakFix targeted execution: current product planner, at most three unique
   supported experiments in ranked order, stop after the first confirmed break.

The generic comparator is secondary context. The primary comparison is fixed
matrix versus BreakFix targeted execution.

## Provider configuration

- Provider: DeepSeek
- Model: `deepseek-v4-pro`
- Thinking: enabled
- Reasoning effort: `high`
- Temperature: omitted for thinking mode
- Structured output: JSON object mode
- Configured completion budget: 12,000 tokens
- Transport retries: at most two retries per request
- Structured-output recovery: at most one deterministic recovery attempt, only
  for length truncation, empty final content, malformed JSON, or schema failure

Both model lanes record provider/model, prompt hash, reasoning/content
separation, finish reason, model calls, input/output/total tokens, latency,
retries, cache telemetry when available, pricing period, and approximate cost.

The generic comparator prompt is `final-generic-comparator-v1` and the product
planner prompt is `breakfix-product-planner-v1`. The frozen runner is
`scripts/run_final_evaluation.py`.

## Frozen primary metric and gate

Primary metric:

> Total executable experiments required to achieve seeded-fault recall of 1.0
> while producing zero false `CONFIRMED BREAK` outcomes on safe controls.

For each lane, `observed_experiments` is the number of deterministic probes that
actually executed. The fixed matrix has 16 × 8 = 128 planned experiments. The
BreakFix budget is three per case, with immediate stop after the first confirmed
break.

The primary result is eligible only when every faulty case reaches
`CONFIRMED BREAK` and no safe control reaches `CONFIRMED BREAK`. An ineligible
result is a FAIL regardless of any arithmetic reduction percentage. When both
lanes are eligible:

`experiment_reduction_percentage = (fixed_experiments - breakfix_experiments) / fixed_experiments × 100`

`experiments_per_confirmed_defect = executed_experiments / confirmed_break_experiments`

No minimum percentage is imposed beyond the claim that targeted execution uses
fewer experiments than the fixed matrix. No claim is made if the gate is
ineligible.

## Outcome and error rules

- `CONFIRMED BREAK` requires deterministic execution evidence: process failure
  or an output mismatch against evaluator-only expected behavior, with command,
  stdout, stderr, exit/timing data, and payload recorded.
- `NO BREAK CONFIRMED` requires every executed supported probe to have complete
  evaluator evidence and to match expected behavior. It is never emitted for an
  unsupported probe or a provider failure.
- `UNSUPPORTED` means the selected experiment has no supported evaluator
  contract. It is not a safe result.
- `ERROR` covers provider/API/timeout failures, malformed or incomplete planner
  output, execution evidence failure, or other runtime failures. It is not a
  product verdict and makes the primary lane ineligible.
- Provider output errors are preserved as `PROVIDER_OUTPUT_ERROR` and never
  become `NO BREAK CONFIRMED` or `UNSUPPORTED`.

## Integrity controls

- The oracle is loaded only by the evaluator process from outside the agent
  workspace.
- The final run starts from a history-free evaluation copy containing the
  public holdout and current product source, with no `.git` directory.
- A separate leakage audit scans public context, prompts, source comments,
  filenames, and trajectories for oracle values and fault labels.
- No manual steering, case selection, rerun, cherry-picking, or post-hoc tuning
  is allowed after the holdout is frozen.
- Raw evaluator records may contain expected outputs and remain evaluator-only.
  Publicly preserved evidence contains trajectories, telemetry, execution
  artifacts, and comparison summaries without oracle fields.

## Reproducibility

The final runner, exact prompts, holdout manifest hash, product checkpoint, and
environment metadata are recorded with the run. A clean setup must be able to
run the deterministic suite, invoke the CLI on the independent sample, replay
confirmed evidence, and re-run the final evaluator when the DeepSeek credential
is supplied.
