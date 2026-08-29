# BreakFix Phase 1.5 exit report

Date: 2026-08-29

Status: MIXED.

Recommendation: NARROW.

The real-agent validation closed the largest Phase 1 gap. It also disproved the
strongest version of the product claim on this five-case benchmark: a competent
same-model generic agent found all four seeded faults, so BreakFix did not improve
fault discovery. BreakFix did preserve a meaningful execution-efficiency result.

## 1. Exact checkpoint

- Canonical project: `C:\\Users\\HomePC\\Desktop\\BreakFix`
- Final Phase 1.5 run: `evidence/phase1.5-20260829T120133Z/`
- Comparison: `evidence/phase1.5-20260829T120133Z/comparison.json`
- Trajectories: `trajectories/phase1.5/baseline/` and `trajectories/phase1.5/breakfix/`
- Deterministic project suite: 12 passing tests
- Final commit hash: reported in the handoff after commit
- Files changed: new Phase 1.5 validator, evaluator, sanitized benchmark workspaces,
  replay artifacts, prompt documentation, rubric correction, changelog, README,
  and tests

## 2. Model and provider actually used

Both agent lanes used the same real model:

- Provider: Codex multi-agent runtime
- Model: `gpt-5.6-luna`
- Reasoning setting: `xhigh`
- Temperature: not configurable through this runtime
- Model calls: 5 baseline calls and 5 BreakFix calls
- Credentials: none stored or required for the captured runtime
- Token usage: unavailable from the runtime
- Monetary API cost: unavailable and not asserted
- Model runtime: unavailable from the runtime; the evaluator records subprocess
  durations, while the replay metadata preserves the missing value as `null`
- Retries: 0 in both lanes

The project has `.env.example` with names only for a future API-backed run. There
was no OpenAI, Anthropic, Gemini, or Ollama credential or local service available
to the Python process. The captured Codex model responses were therefore stored
as replay artifacts and fed through the same validator and deterministic
execution path.

## 3. Exact instructions and tool access

The exact baseline and BreakFix prompts are preserved verbatim in
`docs/phase1.5-prompts.md`. Each prompt was instantiated only with the sanitized
numeric workspace path.

Baseline instruction summary: review the supplied task, before/after code, and
visible tests; run the visible test command; report likely or confirmed defects;
do not use BreakFix's assumption framework or hidden perturbations; return the
specified JSON object.

BreakFix instruction summary: inspect the same supplied context and visible
tests; model assumptions that could be false; propose experiments only from the
six supported catalogue entries; do not judge experiment success; return the
specified structured JSON object.

Both lanes had read-only filesystem inspection and visible test command access.
Neither lane received ground truth, prior evidence, other cases, hidden
perturbation results, or permission to modify files. The BreakFix agent did not
decide whether an experiment succeeded. The deterministic executor did.

## 4. Case-by-case results

The five cases were rerun in sanitized numeric workspaces to avoid names such as
`retry` or `timezone` leaking the intended perturbation.

| Case | Seeded condition | Live baseline | BreakFix proposal and result | Fixed matrix |
| --- | --- | --- | --- | --- |
| case_01 | Empty collection divides by zero | Detected | `input_empty`, `input_boundary_zero`; detected with 2 executions | Detected with 6 |
| case_02 | Duplicate retry charges twice | Detected | `retry_duplicate` plus `input_empty`; detected with 2 executions | Detected with 6 |
| case_03 | Legacy state lacks `tax_rate` | Detected | `state_legacy`; detected with 1 execution | Detected with 6 |
| case_04 | Reordered confirmation remains pending | Detected | `events_reordered`; detected with 1 execution | Detected with 6 |
| case_05 | Safe timezone conversion | False positive | `world_dst`; no confirmed break | No confirmed break with 6 |

Every BreakFix confirmed fault has subprocess evidence. No proposed experiment
was unsupported. The model proposed `world_dst` twice for the safe case through
two separate assumptions; the validator deduplicated the supported ID and ran it
once. That is a recorded normalization, not a hidden execution.

## 5. Full metrics

| Metric | Live baseline | Fixed matrix | Live BreakFix |
| --- | ---: | ---: | ---: |
| Seeded faults discovered | 4/4 | 4/4 | 4/4 |
| Seeded faults missed | 0 | 0 | 0 |
| False positives on safe case | 1 | 0 | 0 |
| False approvals | 0/4 | 0/4 | 0/4 |
| Experiments executed | 0 | 30 | 7 |
| Confirmed failures produced | 0 | 4 | 4 |
| Executable reproduction rate | N/A | 100% | 100% |
| Experiment subprocess runtime | N/A | 35,128 ms | 8,755 ms |
| Model calls | 5 | 0 | 5 |
| Token usage | unavailable | N/A | unavailable |
| Monetary cost | unavailable | N/A | unavailable |

The fixed matrix and BreakFix both achieved complete seeded-fault coverage. The
targeted lane used 7 rather than 30 experiments, 4.29x fewer executions, or
76.7% fewer. The original 5x, 80% reduction did not survive exactly because the
real agent selected one additional supported probe on case_02.

## 6. Parsing, retries, and unsupported assumptions

- Baseline parse failures: 0.
- BreakFix parse or schema failures: 0.
- Agent retries: 0.
- Unsupported experiment proposals: 0.
- Ground-truth leakage: none supplied to either agent.
- Real subprocess executions: yes.
- All five visible case suites: passed.

The validator rejects malformed JSON, records validation failures, marks unknown
experiment IDs unsupported, and executes only supported IDs. It does not translate
an unsupported proposal into a successful result.

## 7. Comparison with Phase 1

Phase 1 used an offline generic surrogate at 2/4 fault detection, a fixed matrix
at 4/4 with 30 experiments, and BreakFix at 4/4 with 6 experiments. Phase 1.5
replaced both reasoning lanes with the same real model. The live baseline rose to
4/4 fault detection but introduced one false positive on the safe timezone case.
BreakFix stayed at 4/4, had no safe-case false positive, and used 7 experiments.

Therefore:

- The 5x experiment-efficiency finding did not survive exactly.
- The broader efficiency advantage did survive: 7 versus 30 executions.
- The discovery advantage did not survive: 4/4 versus 4/4.
- The safe-case precision signal favors BreakFix in this run, but one safe case is
  too small for a reliable claim.

## 8. Load-bearing hypothesis decision

Hypothesis: change-aware assumption falsification finds more meaningful defects
than a generic review or fixed checklist while spending fewer experiments.

Decision: not formally supported. The efficiency half is promising, but the
discovery half failed to beat the live baseline. The correct conclusion is MIXED,
not PASS, and the benchmark must be expanded before deciding whether the
assumption framework adds value beyond a strong generic agent.

## 9. Remaining risks

- Five synthetic cases are insufficient to establish general performance.
- The cases are close to the current six-experiment vocabulary.
- The live model runtime did not expose token usage, cost, or latency.
- Captured replay artifacts are reproducible, but a clean-machine live provider
  invocation is not yet implemented.
- The local Python executor is a development harness, not a production sandbox.
- Output mismatch and environment-dependent behavior need broader classification.
- One safe case cannot characterize false-positive behavior.
- The official instruction PDF itself remains inaccessible locally. The director's
  verified scoring rubric is now recorded, while other PDF-dependent constraints
  remain open.

## 10. Recommended Phase 2 architecture

Narrow the product around evidence-efficient review rather than claiming broad
defect-discovery superiority:

1. Keep the deterministic perturbation catalogue, validator, executor, and
   evidence format as the trust core.
2. Make the model propose and explain assumptions, never classify execution
   success.
3. Add a real API-backed provider with secret isolation, token/cost/latency
   capture, retries, timeouts, and a doctor check.
4. Expand to independent cases that are not selected from the current catalogue.
5. Add multiple safe cases and adversarial false-positive controls.
6. Add a reducer and regression artifact only after a failure is independently
   reproducible.
7. Require human approval before any fix or consequential action.
8. Build UI only after the narrowed evidence workflow beats the baseline on a
   broader benchmark or demonstrates a defensible cost and coverage advantage.

Explicit recommendation: NARROW. Do not pivot away from the mechanism yet, but
do not present it as a proven discovery advantage and do not begin polished UI.
