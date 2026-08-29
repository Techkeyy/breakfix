# BREAKFIX

Phase 0, Phase 1, and Phase 1.5 only. BreakFix is a change-aware assumption
falsification prototype for the micro1 Frontier Engineering Challenge 2026.

> Your tests check what you expected. We test what you forgot to expect.

This checkpoint intentionally contains no polished UI. It proves the risky
comparison first:

1. a real same-model generic baseline review;
2. a fixed six-experiment matrix;
3. a real BreakFix reasoning agent that proposes structured assumptions;
4. deterministic validation, targeted experiment selection, and real subprocess
   execution.

Run it from this directory:

    python scripts/run_phase15.py
    python -m unittest discover -s tests -v

The Phase 1.5 command evaluates captured real-agent replays under
trajectories/phase1.5/ and writes replayable evidence under evidence/<run-id>/.
The sample projects are synthetic and safe to run locally. The captured model
calls used the Codex multi-agent runtime; a direct API key is not required to
replay this checkpoint. A future live API backend still needs to be added for a
clean-machine re-run without the captured replays.

The current deterministic test suite has 12 passing tests. The Phase 1.5 runner
also executes the five visible case suites and records their output in the
evidence bundle.

See:

- docs/hackathon-requirements.md
- docs/product-understanding.md
- docs/project-edge.md
- docs/build-plan.md
- docs/assumptions-and-risks.md
- docs/phase1.5-prompts.md
- docs/phase1.5-exit-report.md

## Phase 1.5 result

Final run: evidence/phase1.5-20260829T120133Z/

| Lane | Fault detection | Experiments |
| --- | ---: | ---: |
| Live generic baseline | 4/4, 100% | 0 hidden probes |
| Fixed matrix | 4/4, 100% | 30 |
| Live BreakFix reasoning agent | 4/4, 100% | 7 |

All five visible case suites passed. The live baseline produced one false
positive on the safe timezone case; BreakFix produced none. Every confirmed
BreakFix fault has captured stdout, stderr, exit status or output mismatch, and
an agent trajectory. The result is MIXED: the 5x efficiency finding did not
survive exactly, but BreakFix still used substantially fewer experiments than
the fixed matrix. The cases are synthetic and the executor is not a production
sandbox.

## Current scope

Supported prototype surfaces are input boundaries, persisted state shape,
duplicate operations, reordered events, and timezone interpretation. The
controlled case contract is a Python app.py module with run(payload). No
GitHub integration, regression-test generation, reducer, fix application,
approval flow, production sandbox, multi-language support, or UI is shipped in
this checkpoint.
