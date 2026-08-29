from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from breakfix.phase2a_prompts import render_prompt
from breakfix.provider import OpenAICompatibleProvider


def main() -> None:
    provider = OpenAICompatibleProvider()
    holdout = PROJECT_ROOT / "benchmark" / "phase2a_holdout"
    for lane in ("baseline", "breakfix"):
        for case_root in sorted(holdout.iterdir()):
            public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
            prompt = render_prompt(lane, str(case_root), public["test_command"])
            response = provider.complete(prompt)
            target = PROJECT_ROOT / "trajectories" / "phase2a" / lane / case_root.name
            target.mkdir(parents=True, exist_ok=True)
            (target / "replay.json").write_text(json.dumps({
                "provider": response.provider,
                "model": response.model,
                "reasoning_effort": provider.reasoning_effort,
                "temperature": provider.temperature,
                "max_output_tokens": provider.max_output_tokens,
                "prompt_id": f"phase2a-{lane}-v1",
                "prompt_file": "docs/phase2a-prompts.md",
                "prompt_workspace": str(case_root),
                "model_calls": 1,
                "runtime_ms": response.latency_ms,
                "latency_ms": response.latency_ms,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": (response.input_tokens + response.output_tokens) if response.input_tokens is not None and response.output_tokens is not None else None,
                "monetary_cost_usd": response.monetary_cost_usd,
                "retries": 0,
                "context": {"public": public, "workspace_files": ["public.json", "before/app.py", "after/app.py", "after/tests"]},
                "tool_access": "provider response only; the prompt grants repository inspection to the model",
                "tool_actions": [],
                "response_text": response.response_text,
            }, indent=2) + "\n", encoding="utf-8")
    print("Phase 2A direct-provider replays written under trajectories/phase2a/")


if __name__ == "__main__":
    main()
