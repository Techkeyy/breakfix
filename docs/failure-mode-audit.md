# Failure-mode audit

| Failure mode | Product behavior | Evidence |
| --- | --- | --- |
| Missing provider credential | Returns an explicit provider error; no product verdict is emitted | `tests/test_provider.py`; `breakfix/provider.py` |
| HTTP/API error | Preserves `PROVIDER_ERROR`; does not reinterpret it as a clean result | Provider contract tests |
| Transport timeout | Preserves provider error and bounded retry metadata | Provider contract tests |
| Empty, truncated, malformed, or schema-invalid response | Allows at most one deterministic structured-output recovery, then emits `PROVIDER_OUTPUT_ERROR` | Provider contract tests; final telemetry |
| Visible test failure | Captures command, stdout, stderr, exit, and timing before planner execution | Product loop tests; final trajectories |
| Process crash during a supported probe | Emits `CONFIRMED BREAK` only with complete deterministic execution evidence | Final q1a, q2b, q4d trajectories |
| Output mismatch during a supported probe | Evaluator can emit `CONFIRMED BREAK` without requiring a crash | Final q3c, q5e, q6f, q7g, q8h trajectories |
| Unsupported assumption or missing evaluator contract | Emits `UNSUPPORTED`; never treats it as safe | Phase 2B contract tests; 56 fixed final probe records |
| No supported planner selection | Emits `UNSUPPORTED`; no clean verdict is claimed | Product loop implementation |
| Generated regression does not reproduce | Confirmed case is downgraded to `ERROR` rather than called valid | `breakfix/product.py`; product tests |
| Candidate fix without approval | Refuses to apply the patch | Product approval-gate test |
| Incomplete fixed evidence | Lane is ineligible rather than passing arithmetic | Final evaluator scoring logic |

The final run recorded zero provider errors, zero execution errors, complete
BreakFix lane contracts for all 16 cases, and zero safe-control confirmed
breaks. The preserved Phase 2B Attempt 1 remains a separate historical output
contract failure and was not silently replaced.
