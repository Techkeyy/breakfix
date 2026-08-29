from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from breakfix.phase2b import PHASE2B_CASE_IDS, holdout_case_dir
from breakfix.phase2b_prompts import PROMPT_IDS, render_prompt
from breakfix.provider import DirectProvider, ProviderError


def _write_replay(target: Path, payload: dict) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "replay.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    provider = DirectProvider()
    if not provider.api_key:
        raise SystemExit(f"Phase 2B preflight failed: set {provider.api_key_env}")
    if provider.requires_external_cost_rates and (provider.input_rate is None or provider.output_rate is None):
        raise SystemExit("Phase 2B preflight failed: set BREAKFIX_COST_INPUT_PER_1K and BREAKFIX_COST_OUTPUT_PER_1K")

    for lane in ("baseline", "breakfix"):
        for case_id in PHASE2B_CASE_IDS:
            case_root = holdout_case_dir(PROJECT_ROOT, case_id)
            public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
            prompt = render_prompt(lane, case_root, public["test_command"])
            common = {
                "provider": provider.provider,
                "model": provider.model,
                "reasoning_effort": provider.reasoning_effort,
                "reasoning_mode": provider.reasoning_mode,
                "temperature": provider.temperature,
                "max_output_tokens": provider.max_output_tokens,
                "prompt_id": PROMPT_IDS[lane],
                "prompt_file": "docs/phase2b-prompts.md",
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "prompt_context": {"public": public, "workspace_files": ["public.json", "before/app.py", "after/app.py", "after/tests"]},
                "model_calls": 1,
                "tool_access": "direct provider receives the rendered public context only",
                "tool_actions": [],
                "response_text": "",
            }
            try:
                response = provider.complete(prompt)
                replay = {
                    **common,
                    "runtime_ms": response.latency_ms,
                    "latency_ms": response.latency_ms,
                    "request_timestamp_utc": response.request_timestamp_utc,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "input_cache_hit_tokens": response.input_cache_hit_tokens,
                    "input_cache_miss_tokens": response.input_cache_miss_tokens,
                    "total_tokens": response.total_tokens,
                    "monetary_cost_usd": response.monetary_cost_usd,
                    "pricing_period": response.pricing_period,
                    "input_cache_status": response.input_cache_status,
                    "pricing_source": response.pricing_source,
                    "pricing_retrieved_date": response.pricing_retrieved_date,
                    "pricing_input_rate_per_million": response.pricing_input_rate_per_million,
                    "pricing_output_rate_per_million": response.pricing_output_rate_per_million,
                    "finish_reason": response.finish_reason,
                    "retries": response.retries,
                    "response_text": response.response_text,
                }
            except ProviderError as exc:
                replay = {
                    **common,
                    "runtime_ms": exc.latency_ms,
                    "latency_ms": exc.latency_ms,
                    "request_timestamp_utc": exc.request_timestamp_utc,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "monetary_cost_usd": None,
                    "retries": exc.retries,
                    "api_error": str(exc),
                }
            except Exception as exc:
                replay = {
                    **common,
                    "runtime_ms": None,
                    "latency_ms": None,
                    "request_timestamp_utc": provider.last_request_timestamp_utc,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "monetary_cost_usd": None,
                    "retries": 0,
                    "api_error": f"{type(exc).__name__}: {exc}",
                }
            _write_replay(PROJECT_ROOT / "trajectories" / "phase2b" / lane / case_id, replay)
            if replay.get("api_error"):
                raise SystemExit(f"Phase 2B provider error in {lane}/{case_id}: {replay['api_error']}")
    print("Phase 2B direct-provider replays written under trajectories/phase2b/")


if __name__ == "__main__":
    main()
