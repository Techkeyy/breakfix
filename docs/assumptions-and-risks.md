# BreakFix assumptions and risks

## Load-bearing project hypothesis

A change-aware agent that explicitly infers hidden assumptions and selects
targeted falsification experiments will discover more real change-induced
failures per reasonable testing budget than:

- ordinary generic coding-agent review; and
- a fixed generic adversarial checklist or matrix.

The hypothesis has three parts:

1. Change context improves which assumptions are challenged.
2. Targeted experiments preserve detection while using fewer executions.
3. Deterministic execution evidence is more trustworthy than an agent verdict.

## Test design

The Phase 1 cases were frozen before the final run. Every lane received the
same selected before/after change and the same visible test result. Ground truth
was kept in benchmark/ground_truth.json and was not supplied to the baseline or
BreakFix planner. The evaluator compared the captured execution result to that
private file after the lanes ran.

Primary metric:

    change-induced hidden defect detection rate
    = faulty cases with a confirmed relevant failure / faulty cases

Secondary metrics:

- false approval rate on faulty cases;
- false positive rate on the safe case;
- executable reproduction rate;
- experiment count;
- per-experiment duration;
- visible-suite pass rate.

The matrix and BreakFix lanes use the same experiment library. The matrix runs
all six experiments per case. BreakFix runs only what the planner selects.

## Frozen five-case benchmark

| Case | Surface | Hidden condition | Ground truth |
| --- | --- | --- | --- |
| case_input_boundary | Input | Empty collection after an average refactor | Fault, input_empty raises |
| case_retry_duplicate | Timing | Same request delivered twice after idempotency removal | Fault, retry_duplicate charges 50 instead of 25 |
| case_stale_state | State | Version 1 record lacks tax_rate | Fault, state_legacy raises |
| case_reordered_events | Timing | Confirm arrives before reserve | Fault, events_reordered returns pending instead of confirmed |
| case_timezone_robust | World | UTC instant must be interpreted in a requested timezone | Correct change, world_dst remains open |

The ground-truth file is evaluator data. The planner sees only the diff and
visible-test result. The public case files do not name the hidden fault.

## Phase 1 findings

Final run: phase1-20260829T104633Z.

| Lane | Fault detection | False approvals | False positives | Experiments |
| --- | ---: | ---: | ---: | ---: |
| Offline generic baseline surrogate | 2/4, 50% | 2/4, 50% | 0/1, 0% | 0 |
| Fixed six-experiment matrix | 4/4, 100% | 0/4, 0% | 0/1, 0% | 30 |
| BreakFix targeted planner | 4/4, 100% | 0/4, 0% | 0/1, 0% | 6 |

Interpretation: the targeted prototype preserved the matrix's detection on these
five synthetic cases while using one fifth as many experiments. This is
promising evidence for the targeted-selection mechanism, not evidence of broad
real-world superiority. The baseline is not a live coding-agent run, so the
official load-bearing hypothesis remains unverified.

## Observed planner decisions

- Input boundary: assumed non-empty input; selected input_empty and
  input_boundary_zero. The empty experiment proved the break.
- Retry duplicate: assumed one side effect per request; selected retry_duplicate.
  The output was 50 where the evaluator expected 25.
- Stale state: assumed tax_rate always exists; selected state_legacy. The process
  raised on the old record.
- Reordered events: assumed happy-path event order; selected events_reordered.
  The output was pending where the evaluator expected confirmed.
- Timezone robust: assumed the time calculation must survive timezone
  interpretation; selected world_dst. The correct change passed, so no break was
  reported.

## Risks and mitigations

| Risk | Impact | Mitigation now | Remaining work |
| --- | --- | --- | --- |
| No live baseline model | High | Label the surrogate explicitly; do not claim an official pass | Run a comparable participant-owned agent with the same cases |
| Five synthetic cases | High | Keep claims provisional and ground truth explicit | Expand to 10 or more realistic cases |
| Heuristic planner overfits signals | High | Tests include unrelated diff; no case-ID rules | Test unseen repositories and add semantic agent only after baseline |
| Ground-truth leakage | High | Runner passes only diff and visible result to planner | Add automated context-audit that rejects private paths and expected strings |
| Local subprocess is not a sandbox | High | Synthetic cases only, timeout, reduced environment, no write-back | Containerize before third-party execution |
| Semantic mismatch evaluator | Medium | Expected outputs are private and independent of planner | Define target-project invariants for real repositories |
| No reducer | Medium | Do not call evidence minimal; say experiment reproduction | Implement constrained real reducer |
| No regression test generation | High | Feature is explicitly deferred | Generate and run a test that fails before fix |
| No human approval flow | High | No patch or merge action exists | Add safe working state and explicit approval |
| No model/API cost data | Medium | Record that no model was used | Capture prompt, model, tokens, cost, retries |
| Planner can select extra probes | Medium | Count and report every selected experiment | Tighten ranking and add budget policy |
| Unknown final PDF requirements | High | Requirement matrix marks dependent items UNKNOWN | Obtain and read official PDF before submission |

## Security boundary

The Phase 1 executor is a development harness, not a security boundary. It
uses a fresh Python process, a timeout, a reduced environment, and captured
output. It does not prevent filesystem writes, network access, subprocess
creation, resource exhaustion, or malicious interpreter behavior.

The safe operating rule for this checkpoint is to execute only the included
synthetic cases. A container or equivalent isolation boundary is required before
accepting arbitrary repository code.

## Stop conditions

Stop scaling the product if:

- the live baseline outperforms targeted BreakFix at comparable budget;
- targeted selections do not beat or match the fixed matrix on added cases;
- false positives rise materially on safe changes;
- reproducibility cannot be established from a clean environment;
- a model output is being used as execution truth;
- the sandbox boundary cannot be explained and tested;
- the official requirements conflict with the current architecture.

## Decision

Continue only to the live-baseline and benchmark-hardening phase. Do not start
the polished UI, GitHub integration, fix application, or broad product surface
until the official Phase 1 completeness gate passes.

