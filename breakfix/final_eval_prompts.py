from __future__ import annotations

import json
from pathlib import Path


FINAL_GENERIC_PROMPT_ID = "final-generic-comparator-v1"


def render_final_generic_prompt(case_root: Path) -> str:
    """Render the frozen reasoning-only comparator prompt from public inputs."""
    public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
    before = (case_root / "before" / "app.py").read_text(encoding="utf-8", errors="replace")
    after = (case_root / "after" / "app.py").read_text(encoding="utf-8", errors="replace")
    visible_tests = (case_root / "after" / "tests" / "test_app.py").read_text(
        encoding="utf-8", errors="replace"
    )
    return f'''You are the generic code-review comparator for BreakFix.

Review the selected change using only the public task, before/after source, and
visible tests below. Do not invent hidden test results. Do not propose or run
the BreakFix experiment catalogue. Give a reasoning-only recommendation about
whether the change contains a plausible behavior break.

Return exactly one compact JSON object, with no markdown and no prose outside
the object. Use this schema:
{{
  "recommendation": "POTENTIAL_BREAK|NO_BREAK_FOUND|INCONCLUSIVE",
  "change_summary": "short summary",
  "findings": [{{"summary": "short finding", "evidence": ["file or symbol"]}}],
  "tests_run": [],
  "tool_actions": [],
  "final_conclusion": "short conclusion"
}}

PUBLIC TASK
{public["task"]}

VISIBLE TEST COMMAND
{public["test_command"]}

BEFORE SOURCE: app.py
{before}

AFTER SOURCE: app.py
{after}

VISIBLE TEST SOURCE: tests/test_app.py
{visible_tests}
'''
