from __future__ import annotations

import json
from pathlib import Path


SUPPORTED_CATALOGUE = (
    "input_empty: send an empty collection",
    "input_boundary_zero: send a one-element collection containing zero",
    "retry_duplicate: replay the same request twice",
    "state_legacy: load an older persisted record without a newly assumed field",
    "events_reordered: deliver a valid event sequence in a different order",
    "world_dst: evaluate an absolute timestamp across a daylight-saving boundary",
    "config_missing: remove an optional configuration field",
    "concurrent_duplicate: deliver two concurrent copies through the effect boundary",
)


def _context(case_root: Path) -> str:
    public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
    tests = []
    for path in sorted((case_root / "after" / "tests").glob("*.py")):
        tests.append(f"### {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(
        (
            "PUBLIC TASK\n" + json.dumps(public, indent=2),
            "BEFORE SOURCE\n" + (case_root / "before" / "app.py").read_text(encoding="utf-8"),
            "AFTER SOURCE\n" + (case_root / "after" / "app.py").read_text(encoding="utf-8"),
            "VISIBLE TESTS\n" + "\n\n".join(tests),
        )
    )


def render_prompt(lane: str, case_root: str | Path, test_command: str) -> str:
    root = Path(case_root)
    context = _context(root)
    if lane == "baseline":
        instructions = """You are the generic coding-agent reviewer in the BreakFix Phase 2B evaluation.

Inspect the public task, before source, after source, and visible tests below. Run the visible tests conceptually from the supplied output context if you cannot execute them. Use ordinary coding-agent reasoning only. Do not use BreakFix's experiment catalogue, hidden probes, hidden oracle, or any other case. Do not claim that a change is universally safe and do not claim a hidden failure was executed. This lane is a secondary comparator: report a potential break when source or visible evidence supports one, otherwise report that no break was found or preserve uncertainty.

Return exactly one JSON object and no surrounding prose:
{
  "change_summary": "...",
  "recommendation": "POTENTIAL_BREAK|NO_BREAK_FOUND|INCONCLUSIVE",
  "findings": [{"summary": "...", "severity": "low|medium|high", "evidence": ["path:line or observed visible test result"], "confidence": "low|medium|high"}],
  "tests_run": ["actual command and result or limitation"],
  "tool_actions": [{"action": "inspection or command", "result": "observed result"}],
  "retries": 0,
  "final_conclusion": "..."
}
"""
        prompt_id = "phase2b-baseline-v1"
    elif lane == "breakfix":
        catalogue = "\n".join(f"- {item}" for item in SUPPORTED_CATALOGUE)
        instructions = f"""You are the BreakFix reasoning agent in the Phase 2B evaluation.

Inspect the public task, before source, after source, and visible tests below. Model the material assumptions introduced or relied on by the change. Rank assumptions from highest to lowest expected falsification value. For every ranked assumption, propose exactly one experiment from the supported catalogue. The deterministic evaluator, not you, executes experiments and decides whether a break is real. Do not return SAFE, DEFECT, or a model-decided break outcome. Do not use hidden oracle data, other cases, or experiments outside the catalogue. Do not claim universal safety.

Supported catalogue:
{catalogue}

The deterministic evaluator will deduplicate proposals, keep at most three supported experiments in your ranked order, execute them, and stop immediately after the first confirmed break. Unsupported proposal IDs are recorded as unsupported and are never executed. Keep evidence tied to the visible diff or tests.

Return exactly one JSON object and no surrounding prose:
{{
  "change_summary": "...",
  "assumptions": [{{"id": "stable descriptive id", "statement": "...", "surface": "input|state|timing|world", "evidence": ["path:line or change evidence"], "failure_if_false": "...", "risk": "low|medium|high", "proposed_experiment": {{"id": "supported catalogue id", "parameters": {{}}, "rationale": "..."}}}}],
  "tests_run": ["actual command and result or limitation"],
  "tool_actions": [{{"action": "inspection or command", "result": "observed result"}}],
  "retries": 0,
  "final_conclusion": "..."
}}
"""
        prompt_id = "phase2b-breakfix-v1"
    else:
        raise ValueError(f"unknown lane: {lane}")
    return (
        f"{instructions}\n\nVisible test command: {test_command}\n\n"
        "The following is the complete public case context. It contains no hidden ground truth.\n\n"
        f"{context}"
    )


PROMPT_IDS = {"baseline": "phase2b-baseline-v1", "breakfix": "phase2b-breakfix-v1"}
