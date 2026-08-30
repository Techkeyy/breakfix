# BreakFix submission package

This directory is the curated handoff for the final director gate. It is
supplementary to the repository root and contains the public evidence needed to
review the final result without the evaluator-only truth file.

## Included artifacts

- `../README.md`: product overview, scope, architecture, and limitations.
- `../REPRODUCE.md`: clean-environment setup and exact commands.
- `../docs/`: claims, requirements matrix, changelog, security audit, UI audit,
  trajectory index, final protocol, video script, and shot list.
- `evidence/final-eval-20260829T212423Z/`: the 32-call final evaluation bundle,
  including all public trajectories, telemetry, fixed executions, and summary.
- `evidence/canonical-demo-20260829T223714Z/`: the complete break, replay,
  regression, approval-gated fix, and verification demonstration.
- `evidence/phase2b-20260829T190449Z/`: the preserved historical Attempt 1
  result, including its 32 provider calls and frozen ineligible FAIL.
- `evidence/provider-recovery-smoke-20260829T194240Z/`: the two authorized
  provider-recovery smoke trajectories.
- `evidence/external-acceptance-20260829T201344Z/`: independent non-benchmark
  acceptance evidence.

## Final result

The primary gate is PASS. BreakFix confirmed 8 of 8 seeded faults and 0 of 8
safe false confirmations using 38 targeted experiments versus 128 in the fixed
matrix, a 70.3% reduction in ordinary prose. The exact 70.3125% value is in
the detailed final summary. The generic comparator recorded 7 of 8 fault
recall, and the final provider run recorded 32 live DeepSeek calls, complete
telemetry, two transport retries, and approximate cost of `$0.138005824`.

## Evidence boundary

The copied final and historical Phase 2B evidence is oracle-free. Evaluator-only
expected outputs remain outside this repository in the pre-public backup and
private evaluator workspaces. Historical Phase 1/2A replay remains available
when the private files are supplied through `BREAKFIX_GROUND_TRUTH_PATH` and
`BREAKFIX_PHASE2A_TRUTH_PATH`; those files are not part of this public package.

No provider credential is included. The final video is still a manual submission
action; `../docs/video-script.md` and `../docs/video-shot-list.md` are the
recording specification.
