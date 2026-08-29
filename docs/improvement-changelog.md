# Improvement changelog

This log is maintained during Phase 1. Results refer to the evidence bundle
under evidence/ and are not reconstructed from memory.

| Stage | What we tried | Why | Evaluation cases | Evidence or result | Decision |
| --- | --- | --- | --- | --- | --- |
| 0 | Generic review baseline surrogate | Establish the ordinary-review control | Five frozen cases | 2/4 faulty cases flagged, 0 hidden executions | Keep as a provisional control only |
| 1 | Fixed six-experiment matrix | Measure broad adversarial coverage and execution cost | Five frozen cases | 4/4 faulty cases detected, 30 executions | Keep as the coverage control |
| 2 | First targeted planner | Test diff signals against selected experiments | Five frozen cases | The event-order case was missed because unchanged diff context was ignored; initial run recorded the miss | Fix planner context handling before drawing conclusions |
| 3 | Planner context correction | Allow reasoning over unchanged lines surrounding a changed block and avoid generic payload-index overreach | Five frozen cases | Final run selected event reorder and removed irrelevant input probes from the other cases | Keep the corrected planner |
| 4 | Execution timeout correction | Initial run used 5 seconds for experiments and 10 seconds for visible tests; Python startup caused false timeout records | Five frozen cases | Timeout limits raised to 15 seconds and 30 seconds; final visible suites all passed | Keep explicit bounded timeouts and report them |
| 5 | Final targeted run | Re-run after corrections with evaluator-only ground truth | Five frozen cases | BreakFix 4/4 at 6 executions; matrix 4/4 at 30; baseline surrogate 2/4 | Provisional support for the targeted mechanism; do not build UI yet |
| 6 | Phase 1.5 real-agent validation | Replace the surrogate reasoning lanes with the same real model and preserve captured trajectories | Five sanitized frozen cases | Live baseline 4/4 faults with 1 safe-case false positive and 0 experiments; live BreakFix 4/4 with 7 targeted executions and no safe-case false positive; matrix 4/4 with 30 executions | MIXED: the efficiency result survived, but BreakFix did not improve fault discovery over the live baseline |
| 7 | Phase 2A evidence-quality lock | Test the narrowed evidence-backed thesis on an independent paired holdout | Fourteen numeric cases, 7 faulty and 7 safe | Baseline 13/14 with 100% safe specificity; matrix 14/14 at 112 experiments; BreakFix 11/14 with 7/7 executable fault confirmations at 19 experiments, but 57.1% safe specificity; direct provider telemetry unavailable | FAIL: executable confirmation and raw efficiency are promising, but safe-case verdict precision is worse than the live baseline |
| 8 | Phase 2B final thesis gate preparation | Test whether targeted evidence remains efficient against the fixed matrix with honest no-break outcomes | Fresh 16-case paired holdout, 8 faulty and 8 clean | Frozen primary metric, deterministic three-experiment budget, direct telemetry runner, external evaluator-only oracle, and conditional pre-run leakage audit committed; benchmark awaits an authorized direct-provider credential | Prepared; do not claim results before the direct-provider run |
| 9 | Phase 2B provider amendment | Use the director-authorized provider without changing the frozen benchmark | Same fresh 16-case holdout | DeepSeek V4 Pro adapter, frozen thinking configuration, official peak/off-peak pricing, cache-aware telemetry, and pre-call amendment | Committed before any DeepSeek call; benchmark still awaits local credential configuration |
| 10 | Phase 2B Attempt 1 | Fresh 16-case paired holdout | All 32 DeepSeek calls were preserved. Baseline 16/16 valid; BreakFix 16/16 provider-output errors at the 2,000-token ceiling; fixed matrix 128 executions; no BreakFix experiments | Frozen **FAIL / ineligible**. Preserve permanently; do not interpret the apparent 100% reduction as product improvement |
| 11 | Provider-contract recovery | Two old development cases: one faulty and one safe control | Raised the bounded thinking output budget to 12,000, added JSON mode, reasoning/content separation, one deterministic structured-output recovery, explicit provider-output errors, isolated execution, telemetry, and generated regression evidence | Engineering smoke **PASS**: faulty case confirmed a break after one probe; control completed without a confirmed break |

## Current conclusion

The Phase 2A run confirms that deterministic execution can turn targeted
assumptions into seven executable fault proofs using 19 probes instead of the
matrix's 112. It does not confirm a precision advantage: the live baseline
scored 13/14 with all safe cases accepted, while BreakFix scored 11/14 because
three safe cases became inconclusive after extra probes. The decision is FAIL
under the frozen gate. Keep BreakFix narrow and limit Phase 2B to direct
provider telemetry, budget-aware selection, and a fresh paired rerun before any
UI work.

Phase 2B Attempt 1 is a preserved provider/output-contract failure, not a
thesis failure. The bounded recovery smoke passed, authorizing the full product
build. The next final benchmark must be newly generated and independent from
the exposed Phase 2B development cases.
