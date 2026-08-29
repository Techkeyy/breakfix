# BreakFix build plan

This plan follows the build-process skill. The risky technical assumption is
tested before a UI, external integration, or broad architecture is added.

## Flow maps

Technical pipeline:

    ingest selected change
      -> build relative diff
      -> infer assumptions
      -> rank risk
      -> choose targeted experiments
      -> execute changed code in isolation
      -> capture and evaluate result
      -> write evidence
      -> compare lanes

User journey:

    arrive -> choose change -> understand assumptions -> start analysis
      -> see progress -> inspect a proven break or clean result
      -> reproduce -> generate regression test -> review fix
      -> approve -> verify -> decide whether to merge

The Phase 1 artifact implements the technical flow and the comparison gate. It
does not implement the final interface journey.

## Six pre-build answers

- Primary user: a developer or coding agent responsible for a real code change.
- Job: find a change-induced failure the existing tests did not cover.
- Primary action: analyze the selected change.
- Minimum information needed: before/after code, visible tests, and a runnable
  project entrypoint.
- System can infer: changed behavior, likely assumptions, risk, and candidate
  perturbations.
- First visible value: a ranked assumption tied to a real execution result.

## Phases and gates

### Phase 0: requirements and product lock

Scope:

- inspect the canonical directory and preserve useful work if it exists;
- read the required Desktop skills;
- read the authoritative micro1 challenge page;
- record blocked or unknown PDF-dependent requirements;
- write the five required Phase 0 documents;
- define the load-bearing hypothesis and evaluation rubric.

PASS gate:

- requirements matrix names a source for every important confirmed claim;
- unknowns are explicit;
- product understanding names the user, magic moment, MVP, trust boundary,
  and non-goals;
- no UI or broad architecture is built before Phase 1.

Result: PASS for the page-backed requirements and documents. The official
instruction PDF remains UNKNOWN because the linked file was blocked.

### Phase 1: load-bearing prototype

Scope:

- five controlled changed projects;
- four break surfaces: input, state, timing, and world;
- same selected change and visible tests for every lane;
- offline generic baseline lane;
- fixed matrix lane with six reusable experiments;
- BreakFix lane with assumption inference and targeted selection;
- fresh subprocess execution with timeout and captured output;
- evaluator-only ground truth;
- JSON evidence, logs, and trajectories;
- deterministic unit tests.

PASS gate:

- all five visible test suites pass;
- the fixed matrix runs every declared experiment on every case;
- the targeted lane executes only planner-selected experiments;
- every claimed break has a process failure or output mismatch artifact;
- correct case produces no confirmed break;
- metrics and experiment counts are computed from the evidence bundle;
- planner behavior is covered by tests.

Official completeness sub-gate:

- a real comparable coding-agent baseline has run on the same cases;
- model, prompt, tool set, runtime, and cost are recorded;
- traces satisfy the challenge requirement.

Result:

- Prototype mechanics PASS in run phase1-20260829T104633Z.
- Official completeness sub-gate FAIL because no live model credentials or
  comparable agent runtime was available. The implemented baseline is labeled
  offline deterministic surrogate.

### Phase 2: real-agent and benchmark hardening

Start only after the Phase 1 decision.

Scope:

- connect a participant-owned live coding-agent baseline;
- preserve prompts, model, tools, outputs, timing, and cost;
- add at least five more cases, including an ambiguous and a safe change;
- freeze the evaluation rubric before final runs;
- test malformed model output, timeout, missing dependency, empty diff, and
  unsupported project handling;
- verify that ground truth cannot enter agent context.

PASS gate:

- live baseline and BreakFix use identical case contexts;
- all lanes are independently rerunnable;
- baseline and advanced traces are complete;
- metrics include detection, false approval, false positive, executable
  reproduction, runtime, and cost where available;
- the load-bearing hypothesis is supported or the design is reshaped honestly.

### Phase 3: reduction and regression proof

Scope:

- constrained reducer over supported perturbation dimensions;
- generated regression test in the target test ecosystem;
- prove the regression test fails on unfixed code for the observed reason;
- preserve reduced and unreduced execution evidence.

PASS gate:

- no artifact is called minimal unless a documented reducer attempted it;
- generated tests run and reproduce the original issue;
- false or irrelevant generated tests are rejected.

### Phase 4: fix proposal and approval

Scope:

- candidate patch in a safe temporary working state;
- human approval checkpoint;
- replay exact discovered failure;
- rerun relevant original tests;
- report success, failure, or unresolved state.

PASS gate:

- no silent repository mutation;
- no merge or push;
- “fixed” is emitted only after the old reproduction passes and the relevant
  suite passes.

### Phase 5: product interface

Scope:

- one focused flow: connect/open project, choose change, analyze, inspect
  evidence, approve verification;
- loading, success, empty, and error states;
- accessible responsive design specific to a developer tool;
- no dashboard or chatbot shell unless the workflow proves it needs one.

PASS gate:

- primary action is obvious in five seconds;
- a first-time user reaches a real result in 90 seconds on fixture data;
- rendered desktop and mobile views are visually inspected;
- UI claims match evidence.

### Phase 6: reproducibility and submission readiness

Scope:

- clean-machine setup;
- pinned runtime and dependencies;
- doctor command;
- benchmark command;
- README grounded in measured evidence;
- final requirement and submission matrix;
- video plan and agent traces.

PASS gate:

- fresh environment runs baseline, BreakFix, and evaluation;
- every claim maps to evidence;
- no credentials are present;
- public repository/archive and submission form requirements are rechecked.

## Spending order

1. Prove the assumption-to-experiment mapping.
2. Complete the real execution loop.
3. Add a live comparable baseline.
4. Harden benchmark independence and error paths.
5. Add reduction, regression, approval, and verification.
6. Build the one focused interface.
7. Polish only after the proof is stable.

## Cut list

Do not build yet:

- GitHub integration;
- repository-wide scanning;
- additional languages;
- CI integrations;
- a persistent database;
- autonomous fixes or merge;
- a broad agent chat;
- extra break surfaces beyond the four in Phase 1;
- visual polish that hides missing evidence.

## Current decision

The prototype mechanics deserve a second experiment with a real baseline.
Do not lock the product or start the polished app until that baseline is
available and the five-case comparison is rerun.

