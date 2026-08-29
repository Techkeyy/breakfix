# BREAKFIX

BreakFix is a change-aware assumption falsification prototype for the micro1
Frontier Engineering Challenge 2026.

> Stop guessing what might break. Prove what actually does.

This checkpoint tests a narrow claim: BreakFix can turn plausible suspicions
into executable evidence while spending fewer targeted experiments than a fixed
matrix.

It compares:

1. a same-model generic baseline review;
2. a fixed eight-experiment matrix;
3. a BreakFix reasoning agent that proposes structured assumptions;
4. deterministic validation, targeted selection, and real subprocess execution.

## Quickstart

Run from this directory:

    python -m unittest discover -s tests -v
    python scripts/run_phase2a.py

The Phase 2A command evaluates the fresh 14-case holdout under
`trajectories/phase2a/` and writes evidence under `evidence/<run-id>/`. The
committed replay inputs let the evaluation run without a provider credential.
To capture new direct-provider responses, configure `.env` from `.env.example`
and run `python scripts/run_phase2a_live.py`.

The current deterministic suite has 15 passing tests. All sample projects are
synthetic and safe to run locally. The direct provider path is implemented, but
the final Phase 2A run used the same live Codex multi-agent runtime for both
lanes because this environment had no authorized external provider credential.
Provider tokens, latency, and cost are therefore reported as `null`.

## Phase 2A result

Final run: `evidence/phase2a-20260829T154132Z/`

| Lane | Correct verdicts | Fault recall | Safe specificity | Experiments |
| --- | ---: | ---: | ---: | ---: |
| Live generic baseline | 13/14, 92.9% | 6/7, 85.7% | 7/7, 100% | 0 |
| Fixed matrix | 14/14, 100% | 7/7, 100% | 7/7, 100% | 112 |
| Live BreakFix reasoning agent | 11/14, 78.6% | 7/7, 100% | 4/7, 57.1% | 19 |

BreakFix confirmed all seven faulty cases with executable evidence and used
17.0% as many experiments as the matrix. Its extra safe-case probes made three
safe cases inconclusive. Under the frozen protocol this is **FAIL** for Phase
2A, not a product lock. The honest thesis is evidence-backed falsification plus
potential efficiency; precision against a competent baseline remains unproven.

## Phase 1.5 result

Final run: `evidence/phase1.5-20260829T120133Z/`

| Lane | Fault detection | Experiments |
| --- | ---: | ---: |
| Live generic baseline | 4/4 | 0 hidden probes |
| Fixed matrix | 4/4 | 30 |
| Live BreakFix reasoning agent | 4/4 | 7 |

Phase 1.5 was MIXED: the live baseline matched BreakFix on seeded-fault
discovery, while BreakFix used substantially fewer experiments than the matrix.

## Evidence and scope

The frozen scoring rules are in `docs/phase2a-evaluation-protocol.md`, exact
prompts are in `docs/phase2a-prompts.md`, and the complete 35-item stop report
is in `docs/phase2a-exit-report.md`.

Supported prototype surfaces are input boundaries, persisted state shape,
duplicate operations, reordered events, timezone interpretation, configuration,
and concurrent delivery. The controlled case contract is a Python `app.py`
module with `run(payload)`.

No GitHub integration, regression-test generation, reducer, fix application,
approval flow, production sandbox, multi-language support, or UI is shipped in
this checkpoint.
