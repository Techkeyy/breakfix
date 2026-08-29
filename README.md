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
    python -m breakfix.cli doctor
    python -m breakfix.cli analyze C:\\path\\to\\your\\git-project --task "What changed?"
    python -m breakfix.cli serve

The compatible MVP expects a Python project exposing `app.run(payload)` and a
runnable unittest command. It copies the selected project into a sanitized
temporary workspace, strips common credentials, disables dependency
installation by default, bounds subprocess time, captures stdout/stderr, and
writes evidence under `evidence/<run-id>/`. The adapter uses DeepSeek JSON mode
with a bounded 12,000-token thinking budget and at most one structured-output
recovery. Reasoning content is stored separately from final JSON content.

The current deterministic suite has 37 passing tests. To replay a confirmed
failure, run `python -m breakfix.cli reproduce evidence/<run-id>`. A bounded
reducer is available with `reduce`; candidate fixes are proposed but never
applied without an explicit `apply-fix --approved` command. Verification runs
the failing experiment, generated regression, and visible tests against a
separate approved snapshot.

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

No GitHub integration, automatic merge/push, dependency installation, or
multi-language target support is included. The local UI is a focused evidence
review page rather than a chatbot or observability dashboard.

## Phase 2B authorized gate

Phase 2B is authorized narrowly as the last thesis-validation gate. The frozen
primary metric is total targeted experiments required for complete seeded-fault
recall with zero false confirmed breaks. The fresh holdout is 16 paired cases
(8 faulty, 8 clean), the BreakFix budget is three experiments per case, and the
fixed matrix runs all eight supported experiments per case.

The protocol is committed at `73ac4e85f5839890142224eb82679431deb1b20b`; the
provider amendment is documented in `docs/phase2b-provider-amendment.md`. The
audited pre-run implementation and holdout are committed at
`cec684cda4bcbe0b7adc1d159f615a90e35eea60`. The leakage audit is in
`docs/phase2b-leakage-audit.md`. Run the telemetry-capable lane only after
setting the authorized DeepSeek credential in `.env` from `.env.example`:

    python scripts/run_phase2b_live.py
    python scripts/run_phase2b.py

The direct runner records model, input/output tokens, cache telemetry when
available, latency, retries, API errors, peak/off-peak pricing, and approximate
cost. Phase 2B Attempt 1 is permanently preserved as a frozen **FAIL** under
`evidence/phase2b-20260829T190449Z/`: all 16 BreakFix planner outputs exhausted
the old 2,000-token ceiling before final JSON. It is historical evidence, not a
successful 100% reduction and not a thesis verdict.

The subsequent bounded provider-recovery smoke gate passed on two development
cases under `evidence/provider-recovery-smoke-20260829T194240Z/`. It is an
engineering gate only, not benchmark evidence. The final independent benchmark
must use a new holdout after hardening.

The purpose-built independent acceptance trajectory is recorded under
`evidence/external-acceptance-20260829T201344Z/`; it confirmed a real process
failure, generated a reproducible regression, and exercised the reducer without
using benchmark fixture mappings.
