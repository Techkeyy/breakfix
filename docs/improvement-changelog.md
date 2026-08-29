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

## Current conclusion

The deterministic targeted mechanism earned another experiment, and the Phase
1.5 efficiency result survived a same-model run: 7 targeted executions versus 30
for the fixed matrix. The discovery advantage did not survive this benchmark:
the live baseline found all four seeded faults, but produced one false positive
on the safe case. The result is MIXED, not a product lock. Phase 2 should focus
on benchmark independence, safe-case precision, and whether the assumption path
adds useful evidence beyond a competent generic agent before any UI work.
