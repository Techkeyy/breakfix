from __future__ import annotations

import json
from pathlib import Path

from .experiments import EXPERIMENTS


PRODUCT_PROMPT_ID = "breakfix-product-planner-v1"


def _source_context(project_dir: Path, diff: str, task: str, visible_tests: str) -> str:
    changed_files = []
    for line in diff.splitlines():
        if line.startswith("+++ "):
            changed_files.append(line[4:])
    sources: list[str] = []
    for relative in sorted(set(changed_files)):
        if relative.startswith("b/"):
            relative = relative[2:]
        path = project_dir / relative
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="replace")
            sources.append(f"### {relative}\n{content[:20000]}")
    catalogue = [
        {"type": experiment.id, "surface": experiment.surface, "description": experiment.description}
        for experiment in EXPERIMENTS
    ]
    return "\n\n".join(
        (
            "TASK\n" + task,
            "SELECTED CHANGE DIFF\n" + diff[:30000],
            "CURRENT CHANGED SOURCE\n" + ("\n\n".join(sources) if sources else "No changed source was readable."),
            "VISIBLE TEST RESULT\n" + visible_tests[:12000],
            "SUPPORTED EXPERIMENTS\n" + json.dumps(catalogue, indent=2),
        )
    )


def render_product_planner_prompt(project_dir: Path, diff: str, task: str, visible_tests: str) -> str:
    return f"""You are the BreakFix change-analysis planner.

Inspect the selected change, current source, and visible test result. Infer only
material assumptions across these supported surfaces: input, state, timing, or
world. Rank assumptions by falsification value. Propose at most one supported
experiment per assumption. The deterministic engine, never you, decides
whether a break exists. Do not claim DEFECT, SAFE, or a confirmed break.

Return exactly one compact JSON object, with no markdown and no prose outside
the object. Do not include chain-of-thought or duplicated source excerpts.
Use this schema:
{{
  "change_summary": "short summary",
  "assumptions": [
    {{
      "id": "A1",
      "statement": "short assumption",
      "surface": "input|state|timing|world",
      "risk": "low|medium|high",
      "evidence": [{{"file": "path", "location": "line or symbol", "reason": "short reason"}}],
      "failure_if_false": "observable failure",
      "experiment": {{"type": "supported experiment type", "parameters": {{}}}}
    }}
  ]
}}

{_source_context(project_dir, diff, task, visible_tests)}
"""
