# Claims and evidence

This document separates measured claims from product scope. The final run is
`evidence/final-eval-20260829T212423Z/`.

| Claim | Measured result | Evidence |
| --- | --- | --- |
| BreakFix can turn a ranked assumption into executable failure evidence | 8 of 8 final faulty changes reached `CONFIRMED BREAK`; every confirmed case has command, payload, stdout, stderr, exit, timing, and result evidence | `evidence/final-eval-20260829T212423Z/trajectories/breakfix/`; `docs/failure-mode-audit.md` |
| Targeted execution used fewer probes than the fixed matrix while preserving the frozen gate | 38 targeted experiments versus 128 fixed experiments, a 70.3125% reduction | `evidence/final-eval-20260829T212423Z/final-summary.json` |
| Safe controls avoided false confirmed breaks | 0 of 8 safe controls reached `CONFIRMED BREAK` | `evidence/final-eval-20260829T212423Z/final-summary.json` |
| The generic reasoning comparator is a meaningful secondary baseline | 7 of 8 faulty changes were recommended as `POTENTIAL_BREAK`, with 0 false confirmations on safe controls | `evidence/final-eval-20260829T212423Z/trajectories/baseline/`; final summary |
| The provider path preserved live telemetry | 32 recorded model completion calls, 32 successful structured responses, JSON mode, reasoning content present, 2 transport retries, and approximate cost of `$0.138005824` | `evidence/final-eval-20260829T212423Z/final-summary.json` |
| The final primary gate passed | Fixed matrix eligible, BreakFix eligible, complete seeded-fault recall, zero safe false confirmations, and fewer targeted experiments | `evidence/final-eval-20260829T212423Z/final-summary.json` |

## Boundaries

These results cover the frozen 16-case holdout, four supported surfaces, the
Python `app.run(payload)` contract, and the DeepSeek V4 Pro configuration in
the frozen protocol. They do not establish general defect-detection accuracy,
support for arbitrary languages, or a universal reduction percentage.

The fixed lane recorded 56 `UNSUPPORTED` probe records because the evaluator
only defines expected output contracts for the seeded fault probe on faulty
cases. Unsupported is neither a safe result nor a confirmed break. It is
reported explicitly and excluded from the primary verdict arithmetic.

The final result does not claim that the generic comparator is worse in every
setting. It reports this holdout only: 87.5% seeded-fault recall versus 100%
for BreakFix, with zero safe false confirmations in both lanes.
