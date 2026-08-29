# Phase 2B prompts

The exact rendered prompt templates are implemented in
`breakfix/phase2b_prompts.py`. The direct runner renders the same template for
each numeric case, inserting only `public.json`, before source, after source,
and visible tests. Ground truth is never rendered.

## Generic coding-agent lane

The baseline receives the public task and source context and returns a
reasoning-only recommendation: `POTENTIAL_BREAK`, `NO_BREAK_FOUND`, or
`INCONCLUSIVE`. It is a secondary comparator and cannot claim hidden execution
or universal safety.

## BreakFix lane

BreakFix receives the same public context and returns ranked assumptions, each
with one proposed supported experiment. The deterministic evaluator dedupes
and caps proposals at three per case, executes them, stops at the first
confirmed failure, and decides the outcome from evidence.

Prompt IDs are `phase2b-baseline-v1` and `phase2b-breakfix-v1`. The runner
records a SHA-256 of each rendered prompt in its trajectory metadata.
