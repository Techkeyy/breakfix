# Phase 2B holdout leakage audit

Audit status: **PASS before execution**  
Audit date: 2026-08-29  
Holdout: `benchmark/phase2b_holdout/`  
Reviewer: independent read-only audit path plus a separate review-agent context

## Scope

The audit covered all 16 numeric cases (`h15`–`h30`) and the evaluator-only
oracle at `benchmark/phase2b_ground_truth.json`. It inspected filenames,
directory names, public task metadata, source files, visible test names and
content, comments, source constants, fixture metadata, prompt context, and
recent commit messages. The audit ran before any Phase 2B provider call or
result evaluation.

## Findings

- Case directories and IDs are numeric only. No directory or filename contains
  a fault category, expected breaker, safe/faulty label, or oracle value.
- Public titles and task descriptions use neutral update language. The exposed
  `surface` field identifies an existing supported BreakFix surface; it does
  not disclose the case label or the seeded experiment.
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
- The hidden oracle is a separate benchmark file and is read by the evaluator
  only. It is not copied into case directories, rendered into prompts, or
  included in trajectory context.
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

No obvious benchmark leakage was found. The holdout is cleared for execution.
This audit is immutable evidence of the pre-run state; it must not be edited
after provider execution begins.
