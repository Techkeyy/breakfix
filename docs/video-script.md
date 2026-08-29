# Solution video script, target 4:50

## 0:00 to 0:25: problem

Show an ordinary coding-agent-generated change while its visible tests pass.
Say: “AI can already suggest many things that might be wrong. The expensive
part is proving which suspicions are real.” Then say: “Your tests check what you
expected. BreakFix tests what you forgot to expect.”

## 0:25 to 0:45: simple baseline

Show the generic comparator prompt and its JSON recommendation for the same
change. Say that this lane receives only the public change and visible tests. It
can identify a plausible risk, but it does not receive hidden probes and does
not execute them. Say: “BreakFix does not stop at a warning.”

## 0:45 to 1:15: visible tests and selected change

Run the canonical demo from the terminal and show the visible test pass, the
selected change, and the selected sample project. Then open the local evidence
page, where the saved run is indexed. Do not invent a UI state: use the actual
terminal output and the saved canonical evidence.

## 1:15 to 1:45: assumptions and targeted execution

Show the ranked assumption `input_empty`, the supported perturbation, and the
isolated command. Narrate: “The planner proposes what to attack. The execution
engine decides.” Show the payload, stdout, stderr, exit status, and timing.

## 1:45 to 2:30: confirmed break to regression proof

Show `CONFIRMED BREAK`, expected versus actual behavior, the replay command, the
generated regression test, and the bounded reduced reproduction. State that the
evidence is reproducible and that the reducer does not call a result minimal
unless it attempted reduction.

## 2:30 to 3:25: approval-gated fix and verification

Show the proposed fix, the required human approval, the approved application,
the after-fix replay, and the original visible tests. End the section on
`VERIFIED`. Say: “BreakFix does not silently write back, merge, or push. A
candidate fix crosses an explicit approval boundary.”

## 3:25 to 4:10: measured final evaluation

Show the final summary and trajectory index. Say: “On a fresh opaque holdout,
BreakFix confirmed 8 of 8 seeded faults and 0 of 8 safe controls. It used 38
targeted experiments versus 128 in the fixed matrix, a 70.3% reduction. The
generic comparator recalled 7 of 8 faults with 0 safe false confirmations.”
Show the 32 live DeepSeek calls, 32 structured responses, two transport
retries, and approximate recorded cost of `$0.138005824`.

## 4:10 to 4:35: what changed

Show the changelog entries for the Phase 2B Attempt 1 failure caused by the
2,000-token truncation, the provider recovery, and the final independent
evaluation. Say: “The failed run stays in the record. The recovery changed the
provider contract and evidence handling; it did not change the frozen cases,
prompts, thresholds, oracle, budget, or gate.”

## 4:35 to 4:50: close

Say: “As coding agents become better at imagining possible failures, generating
more suspicions stops being the hard part. The bottleneck becomes deciding
which suspicions are worth executing and proving which failures are real.” Then
say: “Stop guessing what might break. Prove what actually does.” Show
`REPRODUCE.md` and the scope: Python `app.run(payload)`, four supported
surfaces, sanitized local execution, no automatic merge or push. End on the
oracle-free final evidence and the clean-environment reproduction commands.
