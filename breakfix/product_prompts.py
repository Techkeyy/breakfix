from __future__ import annotations

import json
from pathlib import Path

from .experiments import EXPERIMENTS


PRODUCT_PROMPT_ID = "breakfix-product-planner-v3-structured-evidence"


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
        {
            "type": experiment.id,
            "surface": experiment.surface,
            "description": experiment.description,
            "target": experiment.target,
            "perturbation": experiment.perturbation,
            "observable": experiment.observable,
            "failure_predicate": experiment.failure_predicate,
            "observable_schema": experiment.observable_schema,
            "allowed_predicate_operators": experiment.allowed_predicate_operators,
            "capability": experiment.capability,
        }
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
experiment per assumption, but do not force a probe when the catalogue cannot
test the assumption. The deterministic engine, never you, decides whether a
break exists. Do not claim DEFECT, SAFE, or a confirmed break.

An experiment is executable only when its causal contract is explicit and
semantically aligned with the assumption. For every proposal, connect the
assumption to the failure mode, target, exact perturbation, observable,
failure predicate, structured failure predicate, and why this probe tests this
assumption. Surface similarity alone is not enough. The shipped executor has a
Python runtime observable; it
does not observe browser DOM events, downloads, Blob URLs, or arbitrary browser
behavior. Do not map browser-specific hypotheses to generic probes.

Return exactly one compact JSON object, with no markdown and no prose outside
the object. Do not include chain-of-thought or duplicated source excerpts.
Set experiment to null when no supported catalogue probe can genuinely test
the assumption; do not invent or force a probe. Otherwise, use the complete
experiment object shown below and copy the catalogue perturbation exactly.
The structured_failure_predicate field is mandatory. Set it to null only when
the assumption relies on a target exception rather than a structured output
marker. When it is an object, use only a declared observable path, an allowed
operator, and a JSON value of the declared type. Never use code, expressions,
fuzzy matching, or an undeclared field.
Use a canonical array of path segments, including for a top-level field. For
example: {{"path":["reading"],"operator":"equals","value":1}}
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
      "experiment": null
    }}
  ]
}}

When experiment is not null, it must be an object with these exact fields:
{{
  "type": "supported experiment type",
  "target": "relevant file, symbol, or runtime boundary",
  "hypothesis": "the assumption being falsified",
  "perturbation": {{}},
  "observable": "what the executor will inspect",
  "failure_predicate": "the exact observation that counts as the predicted failure",
  "why_this_probe_tests_this_assumption": "causal explanation",
  "structured_failure_predicate": null,
  "parameters": {{}}
}}

{_source_context(project_dir, diff, task, visible_tests)}
"""
