# Phase 2A exit report

Run: `phase2a-20260829T154132Z`  
Decision: **FAIL under the frozen Phase 2A gate**  
Recommendation: keep BreakFix narrow, repair evidence selection and provider
reproducibility before any Phase 2B product expansion.

## 1. Status and recommendation

The fixed matrix achieved perfect verdicts on the independent holdout. The live
baseline was more precise overall than BreakFix. BreakFix confirmed every faulty
case it targeted and used far fewer experiments, but it returned `INCONCLUSIVE`
on three safe cases because it selected extra probes without a case oracle.
This is strong evidence for executable confirmation, not evidence of superior
precision. Do not start UI, GitHub/CI, fixes, reducers, or broad sandboxing.

## 2. Evaluation implementation commit

The evaluator and metric correction used commit `66c0405`.

## 3. Frozen protocol commit

`docs/phase2a-evaluation-protocol.md` was committed before final model
evaluation at `1bce52a`.

## 4. Provider, model, and settings

Both agent lanes used the same `Codex multi-agent runtime`, model
`gpt-5.6-luna`, and `xhigh` reasoning. There were 14 model calls per lane,
zero recorded retries, and the same prompt/context policy. Temperature,
provider latency, input tokens, output tokens, total tokens, and monetary cost
were unavailable from this runtime and are recorded as `null`. The repository
also contains an OpenAI-compatible direct provider at
`breakfix/provider.py` and `scripts/run_phase2a_live.py`; no credential was
available, and the safety review blocked sending local workspace content to a
default external endpoint.

## 5. Benchmark composition

The final holdout contains 14 numeric cases: seven faulty and seven safe. It is
paired across retry/idempotency, empty input, legacy state, reordered events,
timezone conversion, missing configuration, and concurrent duplicate delivery.

## 6. Holdout independence

The previous five Phase 1.5 cases were excluded from primary evidence. Agents
received only one numeric workspace's public task, before/after code, and
visible tests. Ground truth was in `benchmark/phase2a_ground_truth.json` and was
used only by the evaluator. No agent received the truth file, other cases,
trajectories, evidence, or the case-to-experiment mapping.

## 7. Exact prompts

The exact committed prompt templates are in
`docs/phase2a-prompts.md`, with IDs `phase2a-baseline-v1` and
`phase2a-breakfix-v1`. The baseline returns a three-way verdict. BreakFix
returns assumptions and proposed catalogue IDs only; deterministic machinery
decides evidence state and final verdict.

## 8. All lane case results

| Case | Truth | Baseline | Fixed matrix | BreakFix | BreakFix selected | Confirmed |
| --- | --- | --- | --- | --- | --- | --- |
| h01 | faulty | DEFECT | DEFECT | DEFECT | retry_duplicate | retry_duplicate |
| h02 | safe | SAFE | SAFE | SAFE | retry_duplicate | none |
| h03 | faulty | DEFECT | DEFECT | DEFECT | input_empty | input_empty |
| h04 | safe | SAFE | SAFE | INCONCLUSIVE | input_empty, input_boundary_zero | none |
| h05 | faulty | DEFECT | DEFECT | DEFECT | state_legacy | state_legacy |
| h06 | safe | SAFE | SAFE | INCONCLUSIVE | state_legacy, input_empty | none |
| h07 | faulty | INCONCLUSIVE | DEFECT | DEFECT | events_reordered, retry_duplicate, input_empty | events_reordered |
| h08 | safe | SAFE | SAFE | SAFE | events_reordered | none |
| h09 | faulty | DEFECT | DEFECT | DEFECT | world_dst | world_dst |
| h10 | safe | SAFE | SAFE | SAFE | world_dst | none |
| h11 | faulty | DEFECT | DEFECT | DEFECT | state_legacy, config_missing | config_missing |
| h12 | safe | SAFE | SAFE | INCONCLUSIVE | state_legacy | none |
| h13 | faulty | DEFECT | DEFECT | DEFECT | concurrent_duplicate | concurrent_duplicate |
| h14 | safe | SAFE | SAFE | SAFE | concurrent_duplicate | none |

## 9. Confusion matrices

| Lane | Fault as DEFECT | Fault as SAFE | Fault as INCONCLUSIVE | Safe as DEFECT | Safe as SAFE | Safe as INCONCLUSIVE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 6 | 0 | 1 | 0 | 7 | 0 |
| Fixed matrix | 7 | 0 | 0 | 0 | 7 | 0 |
| BreakFix | 7 | 0 | 0 | 0 | 4 | 3 |

## 10. Primary metric

Evidence-backed correct verdict rate was baseline `13/14 = 92.9%`, fixed matrix
`14/14 = 100%`, and BreakFix `11/14 = 78.6%`. `INCONCLUSIVE` was counted as
incorrect and was not converted to `SAFE`.

## 11. Fault recall

Baseline: `6/7 = 85.7%`. Fixed matrix: `7/7 = 100%`. BreakFix: `7/7 = 100%`.

## 12. Safe-case specificity

Baseline: `7/7 = 100%`. Fixed matrix: `7/7 = 100%`. BreakFix: `4/7 = 57.1%`.

## 13. False positives

Baseline: `0`. Fixed matrix: `0`. BreakFix: `0` direct `DEFECT` false
positives. BreakFix's three safe `INCONCLUSIVE` cases remain primary-metric
errors, even though they are not counted as false positive `DEFECT` claims.

## 14. False approvals

Baseline: `0/7`. Fixed matrix: `0/7`. BreakFix: `0/7`.

## 15. Confirmed-failure rate

Baseline: `0/7 = 0%` because it ran no hidden experiments. Fixed matrix:
`7/7 = 100%`. BreakFix: `7/7 = 100%`.

## 16. Executable reproduction rate

Fixed matrix and BreakFix were both `100%`: every confirmed break had command,
payload/setup, expected and actual output, stdout, stderr, exit/timeout status,
and an evidence path. Baseline reproduction is `null` because it produced no
executions.

## 17. Experiment counts

The fixed matrix ran 8 supported experiments on each of 14 cases, for `112`.
BreakFix ran `19` validated supported experiments. Baseline ran `0` hidden
experiments.

## 18. Experiments per confirmed defect

Fixed matrix: `112/7 = 16.0`. BreakFix: `19/7 = 2.71`. Baseline: `null`.

## 19. Runtime

Subprocess execution runtime was fixed matrix `105327 ms` and BreakFix
`21931 ms`. Baseline hidden-execution runtime is `0 ms`. Model runtime and
latency were unavailable and remain `null`.

## 20. Tokens and cost

Input tokens, output tokens, total tokens, and monetary cost are `null` for both
model lanes. The Codex runtime exposed no billing telemetry. No token or cost
estimate is claimed.

## 21. Evidence and trajectory paths

The complete comparison is
`evidence/phase2a-20260829T154132Z/comparison.json`. Per-case lane evidence is
under `evidence/phase2a-20260829T154132Z/{baseline,fixed-matrix,breakfix}/`.
Each selected experiment has `result.json`, `stdout.log`, and `stderr.log`.
Agent trajectories are under `evidence/phase2a-20260829T154132Z/{baseline,breakfix}/hXX/trajectory.json` and the committed replay inputs are under
`trajectories/phase2a/{baseline,breakfix}/hXX/replay.json`.

## 22. Cleared examples

The strongest cleared examples were h02 `retry_duplicate`, h08
`events_reordered`, h10 `world_dst`, and h14 `concurrent_duplicate`. Each
produced an exact expected output and a `CLEARED` evidence record. h04 and h06
also cleared one relevant experiment, but their extra selected probes caused a
conservative final `INCONCLUSIVE` verdict.

## 23. Confirmed breaks

BreakFix confirmed h01 `retry_duplicate`, h03 `input_empty`, h05
`state_legacy`, h07 `events_reordered`, h09 `world_dst`, h11
`config_missing`, and h13 `concurrent_duplicate`. Every one has a real
subprocess failure or exact output mismatch in its per-experiment evidence
directory. No prose-only suspicion was promoted to a confirmed break.

## 24. Inconclusive and unsupported items

BreakFix was `INCONCLUSIVE` on h04 because `input_empty` cleared but the extra
`input_boundary_zero` proposal had no case oracle; on h06 because
`state_legacy` cleared but the extra `input_empty` proposal had no oracle; and
on h12 because `state_legacy` had no oracle for the configuration change. The
model proposed no invalid catalogue ID in this run. Baseline h07 was also
`INCONCLUSIVE` because it identified a plausible order regression without
executing a hidden test.

## 25. Comparison to Phase 1.5

Phase 1.5 used five cases: baseline `4/4` fault discovery with one safe-case
false positive, BreakFix `4/4` with no safe false positive, and 7 BreakFix
experiments versus 30 matrix executions. Phase 2A used a fresh 14-case paired
holdout: baseline `6/7` fault recall and 100% safe specificity, BreakFix `7/7`
fault recall and 57.1% safe specificity, with 19 BreakFix experiments versus
112 matrix executions. The direction changed from a mixed efficiency win to a
clear efficiency win with a safe-verdict precision loss.

## 26. Revised thesis status

“BreakFix turns plausible suspicions into evidence-backed conclusions” is
partially supported: targeted execution confirmed all seven faulty cases and
preserved uncertainty on three safe cases. “BreakFix is more precise than a
competent coding agent” is not supported. The honest thesis remains evidence-
backed falsification plus potential efficiency, with safe-case precision still
unproven.

## 27. Efficiency status

The raw volume threshold passed: `19/112 = 17.0%`, below the frozen 50% cap,
and `2.71` experiments per confirmed defect was below the frozen 3.0 cap.
However, comparable quality failed because BreakFix safe specificity was 42.9
percentage points below the matrix, exceeding the frozen five-point allowance.
Therefore the full efficiency gate is **FAIL**, despite strong experiment
volume reduction.

## 28. Biggest risk

The biggest product risk is over-selection: BreakFix can propose a relevant
probe plus extra supported probes that lack a case oracle, turning a genuinely
safe change into `INCONCLUSIVE`. The biggest reproducibility risk is the lack
of direct provider token/latency/cost telemetry.

## 29. Exact Phase 2B scope

If the director authorizes Phase 2B, scope it to three items only: (1) run the
same prompts through an authenticated direct provider with model, token,
latency, and cost telemetry; (2) add a deterministic budget/stop policy that
executes the highest-risk relevant assumption and does not penalize a cleared
case with unrelated oracle-less probes; and (3) rerun a newly reviewed paired
holdout of at least 14 cases with the same frozen scoring rules. No UI, GitHub,
CI, fixes, reducers, multilingual support, or large sandbox is in scope.

## 30. Stop decision

Stop after Phase 2A. Do not interpret the matrix’s perfect score as product
readiness or BreakFix’s experiment reduction as a PASS. The next change needs
director authorization under the narrow Phase 2B scope above.

## 31. Evidence quality examples

For h01, `retry_duplicate` exited successfully but returned actual
`{"total_charged": 50}` against expected `{"total_charged": 25}`, producing a
confirmed mismatch. For h03, `input_empty` exited non-zero with the captured
`ValueError` traceback. For h13, `concurrent_duplicate` returned two accepted
effects instead of one. The corresponding `result.json` files preserve the
command, payload, status, streams, expected value, and actual value.

## 32. Requirements matrix status

The requirements matrix now records Phase 2A as a fresh independent benchmark,
the frozen protocol, the direct-provider implementation, and the unavailable
telemetry warning. The coding-agent, trajectory, reproducibility, and evidence
claims are updated without claiming direct API execution.

## 33. Changelog lesson

The Phase 2A lesson is not “BreakFix finds more bugs.” The live baseline and
BreakFix both exposed the faulty controls, while deterministic execution was
what converted BreakFix proposals into proof. The remaining work is to preserve
that proof while avoiding unnecessary safe-case inconclusiveness.

## 34. Known limitations

The holdout is synthetic Python, the executor is a development harness rather
than a security sandbox, the Codex replay text was normalized into the committed
contract-preserving artifacts, and direct provider telemetry was unavailable.
These limits are explicit and prevent a broad real-world claim.

## 35. Director decision requested

The evidence supports retaining BreakFix’s narrow evidence-backed falsification
mechanism, but not promoting it to a product build. The exact next decision is
whether to authorize Phase 2B scope item 1 (direct provider telemetry), item 2
(budget-aware safe-case selection), and item 3 (a second independently reviewed
paired holdout). Until then, the project stops here.
