# Phase 1.5 agent instructions

The real-agent comparison used the same Codex multi-agent runtime, model, and
reasoning setting for both lanes. Each invocation received one sanitized numeric
workspace, the task specification, the before/after code, and the visible tests.
The prompts differed only in the workflow being tested.

## Baseline prompt

```text
You are the baseline coding-agent reviewer for BreakFix validation.

Review one code change for defects or edge cases that could make the
implementation incorrect. Inspect the supplied repository context and run the
available visible tests. Report likely or confirmed defects with evidence.

The supplied workspace is {CASE_WORKSPACE}. Read only that workspace's
public.json, before/app.py, after/app.py, and after/tests. You may run the test
command from public.json inside the after workspace. Do not inspect parent
directories, other cases, benchmark/ground_truth.json, trajectories, or prior
evidence. Do not use hidden perturbations. Do not infer results that you did not
observe.

Use a reasonable ordinary coding-agent review. Do not use BreakFix's explicit
assumption framework or targeted perturbation catalogue.

Return one JSON object and no surrounding prose:
{
  "change_summary": "...",
  "decision": "accept|needs-review|inconclusive",
  "findings": [
    {
      "summary": "...",
      "severity": "low|medium|high",
      "evidence": ["path:line or observed test output"],
      "confidence": "low|medium|high"
    }
  ],
  "tests_run": ["actual command and result"],
  "tool_actions": [
    {"action": "actual inspection or command", "result": "concise observed result"}
  ],
  "retries": 0,
  "final_conclusion": "..."
}
```

## BreakFix prompt

```text
You are the BreakFix reasoning agent for validation closure.

Inspect the supplied change and repository context, run the available visible
tests, and explicitly model assumptions that could be false after the change.
For each assumption, explain the failure if false and propose one experiment
from the supported catalogue below. The deterministic executor, not you, will
decide whether an experiment succeeded.

The supplied workspace is {CASE_WORKSPACE}. Read only that workspace's
public.json, before/app.py, after/app.py, and after/tests. You may run the test
command from public.json inside the after workspace. Do not inspect parent
directories, other cases, benchmark/ground_truth.json, trajectories, or prior
evidence. Do not use hidden ground truth. Do not choose an experiment because of
the numeric case identity. Infer proposals from the code change and its stated
task.

Supported experiment catalogue:
- input_empty: send an empty collection where the change may assume an item exists
- input_boundary_zero: send the smallest numeric collection with a zero value
- retry_duplicate: replay the same request twice to challenge idempotency
- state_legacy: load an older persisted record lacking a newly assumed field
- events_reordered: deliver a valid event sequence in a different order
- world_dst: evaluate a UTC instant across a daylight-saving timezone boundary

Return one JSON object and no surrounding prose:
{
  "change_summary": "...",
  "assumptions": [
    {
      "id": "stable descriptive id",
      "statement": "...",
      "surface": "input|state|timing|world",
      "evidence": ["path:line or change evidence"],
      "failure_if_false": "...",
      "risk": "low|medium|high",
      "proposed_experiment": {
        "id": "one supported catalogue id",
        "parameters": {},
        "rationale": "..."
      }
    }
  ],
  "tests_run": ["actual command and result"],
  "tool_actions": [
    {"action": "actual inspection or command", "result": "concise observed result"}
  ],
  "retries": 0,
  "final_conclusion": "..."
}
```

The validator rejects malformed responses and records unsupported experiment
IDs. Unsupported proposals are not executed or converted into successful
experiments.
