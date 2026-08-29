# BreakFix product understanding

Status: Phase 0 understanding for the Phase 1 prototype, written before
building a UI.

## One sentence

BreakFix helps developers and coding agents challenge the assumptions introduced
by a real code change by selecting and executing targeted failure experiments.

## The problem in plain language

A developer changes code, runs the existing tests, and sees green. The tests
cover the examples the team remembered. They often do not cover an empty list,
an older saved record, a duplicate request, a reordered event, or a machine in a
different timezone.

For example, a developer changes a total calculation to read a newly added
field. The current test data contains that field, so the suite passes. A user
still has an older saved record without it. The first real request after
deployment crashes. The code was not obviously careless. The missing assumption
was never written down.

A normal review can point at suspicious code. A fuzzing tool can generate lots
of inputs. A test generator can add cases. BreakFix is narrower: it starts from
the selected change, names the behavior and the assumptions it now depends on,
chooses a small set of plausible ways to violate those assumptions, executes the
experiments, and keeps the failure evidence.

## Before and after

Before:

    select a diff -> run expected tests -> trust green -> discover edge failure later

BreakFix intervenes:

    select a diff
      -> infer changed assumptions
      -> rank risk
      -> select targeted perturbations
      -> execute each in an isolated subprocess
      -> compare observed output or failure with an evaluator oracle
      -> store replayable evidence

After:

    the developer sees which assumption was challenged, what actually happened,
    and the exact experiment that established the result.

The Phase 1 harness is not yet a developer product. It proves this loop on five
controlled Python projects.

## Actors

| Actor | Provides or receives | Directly uses the interface? |
| --- | --- | --- |
| Developer | Selects the change and reviews evidence | Yes, eventually |
| Coding agent | Reads change context and proposes assumptions | Indirectly in Phase 1 traces |
| Baseline reviewer | Reviews the same diff with ordinary generic review instructions | No UI; recorded lane |
| BreakFix planner | Infers and ranks assumptions and selects experiments | No UI; recorded lane |
| Target repository | Contains the before and after code plus visible tests | No |
| Experiment executor | Runs the after version with a perturbation | No |
| Evaluator | Holds private ground truth for controlled benchmark cases | No |
| Evidence store | Keeps change, assumptions, experiment, execution, and comparison records | No |

## Complete journey

### Arrival and understanding

User action: open the project and choose a real change.

System action: identify the selected diff, changed files, nearby code, tests, and
configuration. Phase 1 uses a pair of before and after app.py files plus visible
unittest tests.

### Action

User action: ask BreakFix to find what could break.

System action: infer assumptions from the selected change, rank them, and map the
highest-risk assumptions to a small experiment library.

### Processing

User action: watch the run or wait for it to finish.

System action: run each selected perturbation in a fresh subprocess with a
bounded timeout, a restricted environment, captured stdout and stderr, and no
ground truth in the planner context.

### Feedback

User action: inspect the assumption and experiment.

System action: show the statement being challenged, why it was selected, the
input perturbation, the exit status, output, error, and duration.

### Result

User action: decide whether the finding is worth acting on.

System action: preserve the observed result and evaluation metadata under a
timestamped evidence directory. A later phase will add a reduced reproduction,
regression test, proposed patch, approval checkpoint, and verification replay.

## Magic moment

The magic moment is a previously green change producing a concrete, reproducible
failure when a targeted assumption is violated, with the assumption and
experiment explaining why that failure matters.

In the final product, the moment should happen within the first 90 seconds on a
small local project. In Phase 1, the moment is present in the final evidence
bundle, not in a UI.

## Core loop

    change -> assumption -> experiment -> execution -> evidence

The verdict is not a model opinion. The planner proposes what to try. The
runtime records what happened. The evaluator labels controlled benchmark
outcomes against private ground truth.

## Technical pipeline

    case loader
      -> selected before/after source
      -> diff builder
      -> assumption planner
      -> risk ranking
      -> targeted experiment selector
      -> subprocess executor
      -> evaluator-only comparison
      -> evidence writer
      -> comparison report

The least certain and load-bearing module is the assumption-to-experiment
mapping. If the planner selects irrelevant or no experiments, the product falls
back to a generic matrix and loses its wedge. Phase 1 tests that module before
any UI or integration work.

## Components, purpose first

| Component | Job | Phase 1 technology |
| --- | --- | --- |
| Case loader | Read public cases and evaluator-only ground truth | Python standard library |
| Change collector | Build a relative before/after diff | difflib and pathlib |
| Assumption planner | Infer, rank, and explain hidden assumptions | deterministic Python rules |
| Experiment library | Define reusable input, state, timing, and world perturbations | dataclasses and JSON-shaped payloads |
| Executor | Run target code with timeout and captured output | subprocess |
| Evaluator | Compare observed execution with private benchmark truth | Python standard library |
| Evidence store | Persist logs, JSON records, and trajectories | filesystem |
| Baseline lane | Perform generic diff review without hidden probes | deterministic offline surrogate |
| Tests | Check planner and experiment invariants | unittest |

## Important data

| Data | Meaning | Created by | Read by | Stored | Sensitivity |
| --- | --- | --- | --- | --- | --- |
| Selected diff | The actual code change under test | Change collector | Baseline and BreakFix planner | Evidence change.json | Project code, potentially private |
| Assumption | A condition the changed code appears to rely on | Planner | Experiment selector and user | assumptions.json | Derived project analysis |
| Experiment | A named perturbation and payload | Experiment library | Executor and user | experiments.json and execution | Usually non-sensitive |
| Execution result | Exit code, timeout, output, error, duration | Executor | Evaluator and user | execution result.json and logs | May contain project data |
| Ground truth | Independent expected fault metadata | Benchmark author | Evaluator only | benchmark/ground_truth.json | Must not enter agent context |
| Trajectory | Instructions, context, tool calls, outputs, checkpoints | Lane runner | Judges and maintainers | trajectory.json | Can reveal prompts and code context |
| Comparison | Aggregate rates and experiment budgets | Evaluator | Report and README | comparison.json | Derived result |

The prototype keeps source and evidence local. A future product needs explicit
redaction rules before sending project code to any external model or service.

## State and memory

Initial state: a benchmark case has before code, after code, and visible tests.

Per run: a timestamped evidence directory is created. It contains independent
lane records. An execution is temporary; its captured result is persistent.

Across runs: evidence remains immutable by convention. A later run gets a new
run ID. The benchmark ground truth is not modified during a run.

Future product state: a user would have a selected repository, selected change,
analysis run, finding, approval decision, candidate fix, and verification run.
No such write-back or merge state exists in Phase 1.

## Technology necessity test

| Technology or mechanism | What it does here | If removed | Classification |
| --- | --- | --- | --- |
| Python | Runs the prototype and sample projects | No runnable prototype | Load-bearing |
| Deterministic planner | Maps changed semantics to assumptions | No targeted lane | Load-bearing |
| subprocess | Establishes real execution evidence | Results become speculation | Load-bearing |
| unittest | Verifies visible tests and planner invariants | No baseline test signal | Important |
| Local filesystem | Preserves replayable artifacts | No evidence trail | Load-bearing |
| LLM | Not used in this checkpoint | Prototype still runs; live baseline requirement is unmet | Future, intentionally absent |
| GitHub | Not used | Core workflow still works | Future integration |
| UI | Not used | Phase 1 proof still runs; full product journey is not yet shipped | Future after gate |
| Container sandbox | Not used yet | Local benchmark can run, but arbitrary-code safety is insufficient | Required before third-party execution |

## AI and agent role

Phase 1 has two purposeful lanes:

1. Generic-review baseline. It receives only the selected diff and visible-test
   result. It produces a generic review finding without hidden probes.
2. BreakFix assumption planner. It receives the selected diff and visible-test
   result. It infers assumptions, ranks them, selects experiments, and observes
   execution results.

The implementation is deterministic and offline. It is not a live LLM, and the
evidence records say so. This is useful for proving the control flow and for
keeping a judge reproducible, but it is not a valid substitute for the official
live coding-agent baseline. That unresolved gap is the main Phase 1 blocker.

The model-independent boundary is deliberate: execution, exit status, output,
and evaluator comparison do not depend on model wording.

## Trust model

The user must trust that:

- the selected diff is the intended change;
- the target subprocess is the code that the evidence names;
- the evaluator-only ground truth was authored independently;
- the evidence was not manually edited after execution;
- local execution limits are sufficient for the cases being run.

The user does not have to trust a model to decide that a break occurred. The
prototype can prove a process failure or an observed output mismatch against an
independent oracle.

What remains trusted:

- the benchmark author and ground-truth file;
- the host operating system;
- Python and its subprocess behavior;
- the deterministic planner rules;
- any future model provider if model-generated rationale is added;
- the future sandbox boundary.

The prototype is not secure against arbitrary hostile repository code. It uses
fresh processes, timeouts, a reduced environment, and synthetic cases. It does
not enforce a filesystem or network boundary. Containerized execution is a
prerequisite for third-party repositories.

## Load-bearing assumption

The load-bearing project hypothesis is:

A change-aware agent that explicitly infers hidden assumptions and selects
targeted falsification experiments discovers more real change-induced failures
per reasonable testing budget than ordinary generic review and a fixed generic
matrix.

Exact check:

- freeze five cases and evaluator truth before the run;
- give all lanes the same selected changes and visible tests;
- keep truth out of baseline and BreakFix contexts;
- record baseline findings;
- execute all six reusable experiments in the fixed lane;
- execute only planner-selected experiments in the BreakFix lane;
- compare defect detection, false approvals, false positives, and experiment count.

The Phase 1 result supports the mechanism against the offline baseline surrogate:
BreakFix detected all 4 faulty cases with 6 experiments, while the surrogate
flagged 2 of 4 and performed no hidden experiments. The fixed matrix detected all
4 with 30 experiments. Because no live model baseline was available, the
hypothesis is only provisionally supported and the official gate is incomplete.

## Smallest real MVP

Must have:

- ingest one selected local before/after change;
- infer and rank assumptions from the diff;
- select targeted experiments from four surfaces;
- execute in a bounded subprocess;
- capture the real failure or output;
- keep an evaluator-independent evidence trail;
- compare a baseline, fixed matrix, and targeted lane.

Useful next:

- live comparable coding-agent baseline;
- reducer over actual perturbation dimensions;
- generated regression test that fails before a fix;
- proposed patch with human approval;
- replay and relevant-suite verification;
- containerized third-party repository execution.

Future:

- GitHub change selection;
- multiple languages;
- CI integration;
- richer UI;
- model-generated narrative;
- repository history and durable artifact storage.

## Non-goals

Phase 1 does not:

- scan an entire repository;
- provide generic static analysis or generic test generation;
- claim support for arbitrary languages or repositories;
- call GitHub;
- auto-apply fixes, merge, push, or deploy;
- use a live LLM;
- claim production-grade sandbox security;
- call synthetic benchmark results proof of broad real-world superiority.

## Three explanations

### To a child

When someone changes a machine, BreakFix asks, “What if something unusual
happens?” It tries that unusual thing and shows what really happens.

### To a normal adult

BreakFix checks a software change by trying the situations people forget to
test. It looks at what changed, guesses what the new code is counting on, and
runs small safe experiments. If one makes the program fail, it keeps the exact
recipe so someone else can repeat it. The computer proves the failure; the
assistant only suggests what to try.

### To a developer

BreakFix is a local change-analysis and perturbation-execution harness. A
deterministic planner extracts semantic signals from a relative diff and maps
them to a typed experiment library. Each selected experiment runs the changed
project in a fresh subprocess with a bounded timeout and a sanitized environment.
The evaluator compares the captured result with a private oracle for controlled
cases, while the agent context excludes ground truth. Evidence is stored as
structured JSON plus stdout, stderr, and trajectory records.

## End-to-end story

A developer changes a code path and runs the existing tests. They are green, but
the developer knows the tests reflect remembered examples. They select the
change in BreakFix. BreakFix reads only that change and nearby test context. It
recognizes, for example, a new direct read from persisted state. It states the
assumption that the field always exists, ranks it as risky, and selects the
legacy-state experiment. The executor launches the changed code with an older
record. The code raises a real error. BreakFix saves the input, command, output,
error, timing, and trace. A later product phase would reduce the setup, generate
a regression test, propose a fix, ask the human to approve it, and replay the same
failure before calling the change verified.

## Questions that test understanding

- What is the selected unit of analysis, and why is it not the whole repository?
- Which part proposes an experiment, and which part establishes execution truth?
- What does the baseline receive that BreakFix also receives?
- Why is ground truth stored separately, and what would count as leakage?
- Why is a fixed matrix a useful control but not the product wedge?
- What does BreakFix do when the planner infers no assumption?
- Why does a real subprocess exit matter more than a model saying “break found”?
- Which state is persistent across runs, and which state is temporary?
- What security guarantee does the local prototype not provide?
- What must happen before a proposed fix can be called verified?

