from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderResponse:
    response_text: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    monetary_cost_usd: float | None


class OpenAICompatibleProvider:
    """Minimal direct provider with explicit usage and latency telemetry."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("BREAKFIX_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = os.environ.get("BREAKFIX_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("BREAKFIX_MODEL", "gpt-5.6-luna")
        self.reasoning_effort = os.environ.get("BREAKFIX_REASONING_EFFORT", "xhigh")
        self.temperature = float(os.environ.get("BREAKFIX_TEMPERATURE", "0"))
        self.max_output_tokens = int(os.environ.get("BREAKFIX_MAX_OUTPUT_TOKENS", "2000"))
        self.input_rate = self._optional_float("BREAKFIX_COST_INPUT_PER_1K")
        self.output_rate = self._optional_float("BREAKFIX_COST_OUTPUT_PER_1K")

    @staticmethod
    def _optional_float(name: str) -> float | None:
        value = os.environ.get(name)
        return float(value) if value else None

    def complete(self, prompt: str) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("No direct provider credential: set BREAKFIX_OPENAI_API_KEY or OPENAI_API_KEY")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"direct provider HTTP {exc.code}: {detail}") from exc
        latency_ms = round((time.perf_counter() - started) * 1000)
        usage = payload.get("usage") or {}
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        cost = None
        if isinstance(input_tokens, int) and isinstance(output_tokens, int) and self.input_rate is not None and self.output_rate is not None:
            cost = (input_tokens / 1000 * self.input_rate) + (output_tokens / 1000 * self.output_rate)
        choices = payload.get("choices") or []
        if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
            raise RuntimeError("direct provider response did not contain choices[0].message.content")
        return ProviderResponse(
            response_text=choices[0]["message"]["content"],
            provider="openai-compatible",
            model=payload.get("model", self.model),
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            latency_ms=latency_ms,
            monetary_cost_usd=cost,
        )
