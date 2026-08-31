# Post-hardening independent evaluation protocol

Status: **prepared; authorization required before any live benchmark call**

This protocol is separate from the preserved Phase 2B and final-evaluation
results. It does not alter their cases, prompts, oracle, thresholds, budgets,
or PASS/FAIL decisions.

## Pre-execution artifact completion amendment

The initial post-hardening execution attempt stopped before any provider call
because the required fresh independent holdout and external oracle had not yet
been created. This amendment records completion of those missing artifacts
before evaluation: a new public-safe 16-case holdout and a fresh oracle stored
outside the repository are being sealed, then audited in a history-free
workspace.

This is an artifact-completion amendment only. It does not change the
benchmark contract, prompts, oracle semantics, thresholds, metrics, provider,
model, reasoning setting, three-experiment product budget, 32-call budget, or
PASS/FAIL logic. The prior stopped attempt remains a no-call stop and is not a
result.

## Scope

- Use a newly sealed, opaque 16-case paired holdout: 8 seeded faults and 8
  clean controls, distinct from the preserved Phase 2B and final runs.
- Keep evaluator truth outside the agent-visible workspace and load it only in
  the independent evaluator.
- Use the post-hardening planner contract with the existing deterministic
  catalogue and a maximum of three selected experiments per case.
- Preserve prompts, trajectories, telemetry, raw execution artifacts, and the
  evaluator comparison summary for every case.
- Do not hand-steer cases, rerun selected cases, inspect truth during agent
  execution, or tune the applicability gate to this holdout.

## Live-call budget

Authorization requested: **32 live DeepSeek calls total**.

- 16 calls for the generic comparator lane, one per case.
- 16 calls for the hardened BreakFix planner lane, one per case.
- Deterministic fixed-matrix execution and independent scoring add no provider
  calls.
- The runner must hard-stop at 32 provider completions, including any bounded
  recovery accounting, and record every attempt.

## Cost estimate

The previous 32-call run recorded approximately `$0.138005824`; that is a
historical measurement, not a promise for this run. Using the configured peak
DeepSeek V4 Pro output rate of `$3.96` per million tokens and the current
12,000-token completion ceiling gives an output-only ceiling of:

`32 × 12,000 × $3.96 / 1,000,000 = $1.52064`

Actual cost will also depend on input tokens, cache hit/miss rates, retries,
and the provider's returned usage fields. The evaluator must report the
provider-reported totals and the adapter's cache-aware estimate.

## Gate

Apply the existing primary gate without changing its thresholds: all faulty
cases must reach `CONFIRMED BREAK`, no clean control may reach `CONFIRMED
BREAK`, every confirmed result must satisfy the semantic applicability,
concrete-observable, target-failure, and replay/regression contracts, and any
provider, harness, or evidence failure makes the lane ineligible.

No live evaluation is authorized by this document. Run it only after explicit
director authorization for the 32 calls.
