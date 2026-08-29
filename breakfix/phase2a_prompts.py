from __future__ import annotations


CATALOGUE = """Supported experiment catalogue:
- input_empty: send an empty collection where the changed path may assume an item exists
- input_boundary_zero: send a smallest numeric collection containing zero
- retry_duplicate: replay the same request twice to challenge idempotency
- state_legacy: load an older persisted record lacking a newly assumed field
- events_reordered: deliver a valid event sequence in a different order
- world_dst: evaluate an absolute timestamp across a daylight-saving timezone boundary
- config_missing: remove an optional configuration field at the dependency boundary
- concurrent_duplicate: deliver two concurrent copies of one request through the effect boundary"""


def render_prompt(lane: str, workspace: str, test_command: str) -> str:
    if lane == "baseline":
        return f"""You are the ordinary coding-agent baseline reviewer for the BreakFix Phase 2A evaluation.

Review one code change for defects or edge cases that could make the implementation incorrect. Inspect the supplied repository context and run the available visible tests. Use ordinary coding-agent reasoning only. Do not use BreakFix's assumption framework, experiment catalogue, hidden probes, or ground truth.

The supplied workspace is {workspace}. Read only its public.json, before/app.py, after/app.py, and after/tests. Run exactly this visible test command from the after workspace when possible: {test_command}. Do not inspect parent directories, other cases, benchmark/phase2a_ground_truth.json, trajectories, or evidence. Do not claim an observed hidden failure that you did not execute. Preserve uncertainty.

Return one JSON object and no surrounding prose:
{{
  "change_summary": "...",
  "verdict": "DEFECT|SAFE|INCONCLUSIVE",
  "findings": [
    {{
      "summary": "...",
      "severity": "low|medium|high",
      "evidence": ["path:line or observed visible test output"],
      "confidence": "low|medium|high"
    }}
  ],
  "tests_run": ["actual command and result"],
  "tool_actions": [{{"action": "actual inspection or command", "result": "concise observed result"}}],
  "retries": 0,
  "final_conclusion": "..."
}}"""
    return f"""You are the BreakFix reasoning agent for the Phase 2A evidence-quality evaluation.

Inspect one change, run its visible tests, and explicitly model assumptions that may be false after the change. For each material assumption, explain the failure if false and propose one experiment from the supported catalogue below. The deterministic executor, not you, decides whether an experiment succeeded. Do not return a model-decided SAFE or DEFECT verdict. Preserve uncertainty.

The supplied workspace is {workspace}. Read only its public.json, before/app.py, after/app.py, and after/tests. Run exactly this visible test command from the after workspace when possible: {test_command}. Do not inspect parent directories, other cases, benchmark/phase2a_ground_truth.json, trajectories, or evidence. Do not choose an experiment because of the numeric case identity. Infer proposals from the code change and task.

{CATALOGUE}

Return one JSON object and no surrounding prose:
{{
  "change_summary": "...",
  "assumptions": [
    {{
      "id": "stable descriptive id",
      "statement": "...",
      "surface": "input|state|timing|world",
      "evidence": ["path:line or change evidence"],
      "failure_if_false": "...",
      "risk": "low|medium|high",
      "proposed_experiment": {{"id": "one supported catalogue id", "parameters": {{}}, "rationale": "..."}}
    }}
  ],
  "tests_run": ["actual command and result"],
  "tool_actions": [{{"action": "actual inspection or command", "result": "concise observed result"}}],
  "retries": 0,
  "final_conclusion": "..."
}}"""
