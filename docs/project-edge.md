# BreakFix project edge

This document uses the project-edge skill to make the wedge explicit before any
polished product work begins.

## Mechanic

BreakFix starts with one real code change. It interprets what behavior changed,
names the assumptions that changed code appears to rely on, ranks those
assumptions, chooses perturbations that can violate them, and executes those
perturbations in isolation. A confirmed break is an execution artifact, not a
model sentence.

## Angle

The angle is change-aware assumption falsification.

The center of gravity is not “AI reviews code” or “AI writes tests.” It is the
translation:

    changed code -> newly implied assumption -> targeted violation -> proven result

The Phase 1 implementation uses deterministic rules to prove the mechanic. A
future model can improve semantic interpretation or narrative, but it must not
replace the execution proof.

## Defensible wedge

The defensible wedge is the evidence boundary around a selected change:

- analysis begins with the changed behavior rather than repository-wide noise;
- each experiment is justified by an assumption inferred from that change;
- the executor records what really ran, including timeout, exit code, output,
  error, and duration;
- a fixed matrix remains available as a control;
- evidence is replayable and ground truth is evaluator-only for benchmark runs;
- the system can say that it does not know instead of claiming a green verdict
  from an unexecuted idea.

This wedge is defensible only if it survives on unseen compatible repositories
and a real coding-agent baseline. Phase 1 has not established those broader
claims.

## Closest adjacent categories and products

| Adjacent category | What it usually optimizes | Where BreakFix differs |
| --- | --- | --- |
| AI code review | Review comments on a diff | BreakFix executes targeted assumption violations |
| Static analysis | Known syntactic or semantic rules | BreakFix tests behavior under changed-world inputs |
| Property-based testing | Broad generated input exploration | BreakFix starts from the change and selects a small risk-shaped set |
| Fuzzing | Volume and input-space exploration | BreakFix prioritizes human-readable assumptions and replayable scenarios |
| Test generation | More tests that resemble existing coverage | BreakFix tests what the existing suite did not encode |
| Mutation testing | Whether tests kill synthetic code mutations | BreakFix perturbs runtime assumptions around the actual change |
| Fault injection | Reliability under predefined infrastructure faults | BreakFix chooses faults from the changed behavior and domain context |
| Runtime verification | Monitoring an executing system against rules | BreakFix creates isolated executions before merge |
| CI and regression systems | Re-running known checks | BreakFix searches for new failure evidence before a regression exists |
| Test management platforms | Organizing cases and results | BreakFix is a focused change-to-proof workflow |
| Autonomous coding agents | Modify code toward a task | BreakFix challenges the modification before a human merge decision |

These are adjacent categories, not claims that each product has identical scope.
A final competitive review should inspect current tools and name concrete
comparators only after the product has a live workflow.

## What BreakFix must not become

BreakFix must not become:

- another AI code reviewer that only writes comments;
- a generic fuzzing service with an AI label;
- a test-generation factory measured by test count;
- a whole-repository warning dashboard;
- a pre-scripted collection of benchmark answers;
- a fake-progress demo whose counts do not match executions;
- a hidden-answer system that leaks ground truth into agent prompts;
- a generic chatbot that asks the developer to invent the test strategy;
- autonomous patching, merging, pushing, or deployment;
- a production observability suite;
- an enterprise test-management platform;
- a broad “works on any repository” claim.

## Positioning test

If the repository name, logo, and colors were changed, the primary workflow would
still make sense because its structure is defined by change, assumption,
experiment, and evidence. That is the identity test for this product.

## Boundary to protect

The following are explicit boundary decisions:

- Four Phase 1 surfaces are enough: input, state, timing, and world.
- The prototype supports a standard Python callable contract for its controlled
  cases.
- The planner does not read ground truth.
- The evaluator may use private truth only to score controlled cases.
- The baseline is labeled an offline surrogate until a live model is wired in.
- A failure is not called minimal until a real reducer has attempted reduction.
- A fix is not called verified until the observed reproduction and relevant tests
  pass after human approval.

