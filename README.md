# BREAKFIX

Phase 0 and Phase 1 only. BreakFix is a change-aware assumption falsification
prototype for the micro1 Frontier Engineering Challenge 2026.

> Your tests check what you expected. We test what you forgot to expect.

This checkpoint intentionally contains no polished UI. It proves the risky
comparison first:

1. an offline generic baseline review;
2. a fixed six-experiment matrix;
3. BreakFix inference, risk ranking, targeted experiment selection, and real
   subprocess execution.

Run it from this directory:

    python scripts/run_phase1.py
    python -m unittest discover -s tests -v

The command writes replayable evidence under evidence/<run-id>/ and prints a
comparison report. The sample projects are synthetic and safe to run locally.
The prototype does not yet execute arbitrary third-party repositories in a
container and does not yet call a live model. Those are explicit limitations,
not hidden capabilities.

The current deterministic test suite has 8 passing tests. The Phase 1 runner
also executes the five visible case suites and records their output in the
evidence bundle.

See:

- docs/hackathon-requirements.md
- docs/product-understanding.md
- docs/project-edge.md
- docs/build-plan.md
- docs/assumptions-and-risks.md

## Phase 1 result

Final run: evidence/phase1-20260829T104633Z/

| Lane | Fault detection | Experiments |
| --- | ---: | ---: |
| Offline generic baseline surrogate | 2/4, 50% | 0 hidden probes |
| Fixed matrix | 4/4, 100% | 30 |
| BreakFix targeted planner | 4/4, 100% | 6 |

All five visible case suites passed, and the safe timezone case produced no
confirmed break. Every confirmed fault has captured stdout, stderr, exit
status or output mismatch, and a trajectory record. The result is provisional:
the baseline is not a live coding-agent run, the cases are synthetic, and the
executor is not a production sandbox.

## Current scope

Supported prototype surfaces are input boundaries, persisted state shape,
duplicate operations, reordered events, and timezone interpretation. The
controlled case contract is a Python app.py module with run(payload). No
GitHub integration, regression-test generation, reducer, fix application,
approval flow, or UI is shipped in this checkpoint.
