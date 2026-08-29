# Phase 2B holdout leakage audit

Audit status: **REMEDIATED / PASS before execution**  
Audit date: 2026-08-29  
Holdout: `benchmark/phase2b_holdout/`  
Reviewer: independent read-only audit path plus a separate review-agent context

## Scope

The first audit found three issues: contiguous odd/even IDs correlated with the
fault label, public `surface`/task text made the target experiment nearly
direct, and the oracle was tracked in the repository. Those issues were
corrected before any model/provider call. The final audit covered all 16 opaque
cases and the external evaluator-only oracle. It inspected filenames,
directory names, public task metadata, source files, visible test names and
content, comments, source constants, fixture metadata, prompt context, and
recent commit messages. The audit ran before any Phase 2B provider call or
result evaluation.

## Findings

- Case directories use opaque, non-correlated IDs (`a6t`, `b8n`, `d1y`, `e0r`,
  `g8p`, `k4d`, `m2v`, `n4k`, `p6h`, `r9c`, `s2m`, `u5j`, `v7c`, `w1s`,
  `xq7`, `z3f`). Public IDs no longer encode fault parity.
- Public titles and task descriptions use neutral update language and omit the
  surface field. The agent must infer the relevant surface from the visible
  source change rather than from a near-direct task-to-catalogue mapping.
- Visible tests use ordinary happy-path names and inputs. They do not mention
  hidden probes, fault labels, expected hidden outputs, or oracle metadata.
- Source files contain no fault comments, fixture labels, expected-output maps,
  or truth booleans. The `concurrent_calls` input is an ordinary public runtime
  parameter required by the already supported concurrency catalogue, not a
  truth label.
- A repository search found no `fault`, `faulty`, `safe`, `oracle`, `ground
  truth`, `expected_outputs`, `fault_experiments`, or `defect` text in the
  agent-visible case workspaces.
- A second search found no hidden-truth fields in any `phase2b_holdout` case.
- The hidden oracle is outside the repository at the private evaluator path
  configured by `BREAKFIX_PHASE2B_TRUTH_PATH`. The evaluator fails closed when
  that path is absent. It is not copied into case directories, rendered into
  prompts, or included in trajectory context.
- Recent commits contain only protocol/evidence history and do not name a
  Phase 2B case label or expected breaker.

## Pairing and mutation review

The fresh holdout has eight pairs: repeated-request behavior, collection
summary behavior, record loading, workflow transitions, timestamp conversion,
configuration loading, delivery claims, and numeric metrics. Each faulty case
is a controlled after-source mutation of a known-correct counterpart; each
safe case preserves the counterpart behavior while making a small refactor.
The hidden oracle maps exactly one supported experiment to each pair.

## Decision

The initial leakage findings were remediated and the final read-only audit found
no obvious answer leakage. The holdout is cleared for execution. This audit is
immutable evidence of the pre-run state; it must not be edited after provider
execution begins.
