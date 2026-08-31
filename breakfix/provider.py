from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEEPSEEK_PRICING_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing/"
DEEPSEEK_PRICING_RETRIEVED_DATE = "2026-08-29"
DEEPSEEK_V4_PRO_PRICES_PER_MILLION = {
    "off-peak": {"cache_hit": 0.022, "cache_miss": 0.66, "output": 1.98},
    "peak": {"cache_hit": 0.044, "cache_miss": 1.32, "output": 3.96},
}


@dataclass(frozen=True)
class ProviderResponse:
    response_text: str
    reasoning_text: str | None
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    monetary_cost_usd: float | None
    retries: int = 0
    physical_attempts: int = 1
    total_tokens: int | None = None
    input_cache_hit_tokens: int | None = None
    input_cache_miss_tokens: int | None = None
    request_timestamp_utc: str | None = None
    pricing_period: str | None = None
    input_cache_status: str | None = None
    pricing_source: str | None = None
    pricing_retrieved_date: str | None = None
    pricing_input_rate_per_million: float | None = None
    pricing_output_rate_per_million: float | None = None
    finish_reason: str | None = None
    reasoning_mode: str | None = None
    response_format: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "response_text": self.response_text,
            "reasoning_text": self.reasoning_text,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "monetary_cost_usd": self.monetary_cost_usd,
            "retries": self.retries,
            "physical_attempts": self.physical_attempts,
            "input_cache_hit_tokens": self.input_cache_hit_tokens,
            "input_cache_miss_tokens": self.input_cache_miss_tokens,
            "request_timestamp_utc": self.request_timestamp_utc,
            "pricing_period": self.pricing_period,
            "input_cache_status": self.input_cache_status,
            "pricing_source": self.pricing_source,
            "pricing_retrieved_date": self.pricing_retrieved_date,
            "pricing_input_rate_per_million": self.pricing_input_rate_per_million,
            "pricing_output_rate_per_million": self.pricing_output_rate_per_million,
            "finish_reason": self.finish_reason,
            "reasoning_mode": self.reasoning_mode,
            "response_format": self.response_format,
        }


@dataclass(frozen=True)
class ProviderAttempt:
    """One provider completion and its structured-output assessment."""

    attempt_number: int
    response: ProviderResponse | None
    provider_error: str | None
    output_failure: str | None
    retry_reason: str | None = None
    physical_attempts: int = 0
    retryable: bool | None = None
    http_status: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "provider_error": self.provider_error,
            "output_failure": self.output_failure,
            "retry_reason": self.retry_reason,
            "physical_attempts": self.physical_attempts,
            "retryable": self.retryable,
            "http_status": self.http_status,
            "response": self.response.as_dict() if self.response else None,
        }


@dataclass(frozen=True)
class StructuredProviderResult:
    """Bounded structured-output recovery result.

    Provider failures and output-contract failures remain explicit. Callers
    must not turn either into a product verdict.
    """

    success: bool
    parsed: dict[str, Any] | None
    final_response: ProviderResponse | None
    failure_code: str | None
    attempts: tuple[ProviderAttempt, ...]

    @property
    def output_contract_status(self) -> str:
        if self.success:
            return "OK"
        return self.failure_code or "PROVIDER_ERROR"

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "parsed": self.parsed,
            "failure_code": self.failure_code,
            "output_contract_status": self.output_contract_status,
            "attempts": [attempt.as_dict() for attempt in self.attempts],
        }


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retries: int = 0,
        latency_ms: int | None = None,
        request_timestamp_utc: str | None = None,
        physical_attempts: int = 0,
        retryable: bool | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retries = retries
        self.latency_ms = latency_ms
        self.request_timestamp_utc = request_timestamp_utc
        self.physical_attempts = physical_attempts
        self.retryable = retryable
        self.http_status = http_status


class DirectProvider:
    """Small provider-neutral adapter for the frozen direct model lanes."""

    def __init__(self) -> None:
        self._load_local_env()
        self.provider = os.environ.get("BREAKFIX_PROVIDER", "deepseek").strip().lower()
        if self.provider not in {"deepseek", "openai-compatible"}:
            raise ValueError("BREAKFIX_PROVIDER must be deepseek or openai-compatible")
        if self.provider == "deepseek":
            self.api_key_env = "BREAKFIX_DEEPSEEK_API_KEY"
            self.api_key = os.environ.get("BREAKFIX_DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
            self.base_url = os.environ.get("BREAKFIX_DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
            self.model = os.environ.get("BREAKFIX_MODEL", "deepseek-v4-pro")
            self.reasoning_effort = os.environ.get("BREAKFIX_REASONING_EFFORT", "high")
            if self.reasoning_effort not in {"low", "high", "max"}:
                raise ValueError("DeepSeek V4 Pro reasoning effort must be low, high, or max")
            self.temperature = None
            self.reasoning_mode = "enabled"
        else:
            self.api_key_env = "BREAKFIX_OPENAI_API_KEY"
            self.api_key = os.environ.get("BREAKFIX_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
            self.base_url = os.environ.get("BREAKFIX_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            self.model = os.environ.get("BREAKFIX_MODEL", "gpt-5.6-luna")
            self.reasoning_effort = os.environ.get("BREAKFIX_REASONING_EFFORT", "xhigh")
            self.temperature = float(os.environ.get("BREAKFIX_TEMPERATURE", "0"))
            self.reasoning_mode = None
        # Thinking models can consume the whole completion budget before
        # emitting their compact JSON. Keep this bounded but large enough for
        # reasoning plus a structured planner result.
        self.max_output_tokens = int(os.environ.get("BREAKFIX_MAX_OUTPUT_TOKENS", "12000"))
        self.input_rate = self._optional_float("BREAKFIX_COST_INPUT_PER_1K")
        self.output_rate = self._optional_float("BREAKFIX_COST_OUTPUT_PER_1K")
        self.last_request_timestamp_utc: str | None = None

    @property
    def requires_external_cost_rates(self) -> bool:
        return self.provider != "deepseek"

    @staticmethod
    def _load_local_env() -> None:
        """Load ignored .env values without overriding explicit process vars."""
        path = Path.cwd() / ".env"
        if not path.exists():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"").strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

    @staticmethod
    def _optional_float(name: str) -> float | None:
        value = os.environ.get(name)
        return float(value) if value else None

    @staticmethod
    def _as_nonnegative_int(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    @staticmethod
    def is_deepseek_peak(timestamp: datetime) -> bool:
        """Return whether a UTC timestamp is in DeepSeek's published peak window."""
        utc_hour = timestamp.astimezone(timezone.utc).hour
        return 1 <= utc_hour < 4 or 6 <= utc_hour < 10

    @classmethod
    def _deepseek_cost(
        cls,
        *,
        input_tokens: int | None,
        output_tokens: int | None,
        cache_hit_tokens: int | None,
        cache_miss_tokens: int | None,
        timestamp: datetime,
    ) -> tuple[float | None, str, str, float | None, float | None]:
        period = "peak" if cls.is_deepseek_peak(timestamp) else "off-peak"
        prices = DEEPSEEK_V4_PRO_PRICES_PER_MILLION[period]
        if input_tokens is None or output_tokens is None:
            return None, period, "unknown-conservative-miss", prices["cache_miss"], prices["output"]

        hit = cache_hit_tokens
        miss = cache_miss_tokens
        if hit is not None and miss is None:
            miss = max(input_tokens - hit, 0)
        elif miss is not None and hit is None:
            hit = max(input_tokens - miss, 0)

        if hit is None and miss is None:
            cache_status = "unknown-conservative-miss"
            input_cost = input_tokens * prices["cache_miss"]
        else:
            hit = hit or 0
            miss = miss or 0
            if hit and miss:
                cache_status = "mixed"
            elif hit:
                cache_status = "hit"
            else:
                cache_status = "miss"
            input_cost = hit * prices["cache_hit"] + miss * prices["cache_miss"]
        cost = (input_cost + output_tokens * prices["output"]) / 1_000_000
        return cost, period, cache_status, prices["cache_miss"], prices["output"]

    def _request_body(self, prompt: str, response_format: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_output_tokens,
        }
        if response_format is not None:
            body["response_format"] = response_format
        if self.provider == "deepseek":
            body["thinking"] = {"type": "enabled"}
            body["reasoning_effort"] = self.reasoning_effort
        else:
            body["temperature"] = self.temperature
            if self.reasoning_effort:
                body["reasoning_effort"] = self.reasoning_effort
        return body

    def complete(self, prompt: str, *, response_format: dict[str, Any] | None = None) -> ProviderResponse:
        if not self.api_key:
            raise ProviderError(f"No direct provider credential: set {self.api_key_env}")
        request_timestamp = datetime.now(timezone.utc)
        request_timestamp_text = request_timestamp.isoformat().replace("+00:00", "Z")
        self.last_request_timestamp_utc = request_timestamp_text
        body = self._request_body(prompt, response_format)
        max_retries = max(0, int(os.environ.get("BREAKFIX_MAX_RETRIES", "2")))
        started = time.perf_counter()
        last_error: str | None = None
        payload: dict[str, Any] | None = None
        physical_attempts = 0
        retryable_error: bool | None = None
        http_status: int | None = None
        for attempt in range(max_retries + 1):
            physical_attempts += 1
            request = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                last_error = f"direct provider HTTP {exc.code}: {detail}"
                http_status = exc.code
                retryable_error = exc.code in {408, 429} or 500 <= exc.code <= 599
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"direct provider transport error: {exc}"
                retryable_error = True
            except ValueError as exc:
                last_error = f"direct provider invalid JSON response: {exc}"
                retryable_error = False
            if retryable_error and attempt < max_retries:
                time.sleep(min(2 ** attempt, 4) + random.uniform(0, 0.25))
            elif not retryable_error:
                break
        if payload is None:
            raise ProviderError(
                last_error or "direct provider request failed",
                retries=max(physical_attempts - 1, 0),
                latency_ms=round((time.perf_counter() - started) * 1000),
                request_timestamp_utc=request_timestamp_text,
                physical_attempts=physical_attempts,
                retryable=retryable_error,
                http_status=http_status,
            )
        latency_ms = round((time.perf_counter() - started) * 1000)
        usage = payload.get("usage") or {}
        input_tokens = self._as_nonnegative_int(usage.get("prompt_tokens"))
        output_tokens = self._as_nonnegative_int(usage.get("completion_tokens"))
        total_tokens = self._as_nonnegative_int(usage.get("total_tokens"))
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        cache_hit_tokens = self._as_nonnegative_int(
            usage.get("prompt_cache_hit_tokens", usage.get("cache_hit_tokens"))
        )
        cache_miss_tokens = self._as_nonnegative_int(
            usage.get("prompt_cache_miss_tokens", usage.get("cache_miss_tokens"))
        )
        if self.provider == "deepseek":
            cost, pricing_period, input_cache_status, input_rate, output_rate = self._deepseek_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_hit_tokens=cache_hit_tokens,
                cache_miss_tokens=cache_miss_tokens,
                timestamp=request_timestamp,
            )
            pricing_source = DEEPSEEK_PRICING_SOURCE
            pricing_retrieved_date = DEEPSEEK_PRICING_RETRIEVED_DATE
        else:
            pricing_period = None
            input_cache_status = None
            input_rate = self.input_rate * 1000 if self.input_rate is not None else None
            output_rate = self.output_rate * 1000 if self.output_rate is not None else None
            cost = None
            if input_tokens is not None and output_tokens is not None and self.input_rate is not None and self.output_rate is not None:
                cost = (input_tokens / 1000 * self.input_rate) + (output_tokens / 1000 * self.output_rate)
            pricing_source = None
            pricing_retrieved_date = None
        choices = payload.get("choices") or []
        if not choices or not isinstance(choices[0], dict) or not isinstance(choices[0].get("message"), dict):
            raise ProviderError(
                "direct provider response did not contain choices[0].message",
                retries=attempt,
                latency_ms=latency_ms,
                request_timestamp_utc=request_timestamp_text,
                physical_attempts=physical_attempts,
            )
        message = choices[0]["message"]
        content = message.get("content")
        reasoning_content = message.get("reasoning_content")
        # A valid provider response may have empty final content when the
        # thinking stream exhausts max_tokens. Return it as an explicit output
        # contract failure so the bounded recovery layer can decide whether to
        # retry; do not hide it as a transport/API error.
        if not isinstance(content, str):
            content = ""
        if not isinstance(reasoning_content, str):
            reasoning_content = None
        return ProviderResponse(
            response_text=content,
            reasoning_text=reasoning_content,
            provider=self.provider,
            model=payload.get("model", self.model),
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            latency_ms=latency_ms,
            monetary_cost_usd=cost,
            retries=attempt,
            physical_attempts=physical_attempts,
            total_tokens=total_tokens,
            input_cache_hit_tokens=cache_hit_tokens,
            input_cache_miss_tokens=cache_miss_tokens,
            request_timestamp_utc=request_timestamp_text,
            pricing_period=pricing_period,
            input_cache_status=input_cache_status,
            pricing_source=pricing_source,
            pricing_retrieved_date=pricing_retrieved_date,
            pricing_input_rate_per_million=input_rate,
            pricing_output_rate_per_million=output_rate,
            finish_reason=choices[0].get("finish_reason"),
            reasoning_mode=self.reasoning_mode,
            response_format=(response_format or {}).get("type") if response_format else None,
        )

    def complete_structured(
        self,
        prompt: str,
        *,
        validator: Callable[[str], dict[str, Any]] | None = None,
        max_recovery_attempts: int = 1,
    ) -> StructuredProviderResult:
        """Complete compact JSON with one deterministic output-contract recovery."""
        return bounded_structured_recovery(
            lambda request_prompt: self.complete(request_prompt, response_format={"type": "json_object"}),
            prompt,
            validator=validator,
            max_recovery_attempts=max_recovery_attempts,
        )


def bounded_structured_recovery(
    complete: Callable[[str], ProviderResponse],
    prompt: str,
    *,
    validator: Callable[[str], dict[str, Any]] | None = None,
    max_recovery_attempts: int = 1,
) -> StructuredProviderResult:
    """Provider-neutral recovery helper for tests and alternate adapters."""
    if max_recovery_attempts < 0:
        raise ValueError("max_recovery_attempts must be non-negative")

    def assess(response: ProviderResponse) -> tuple[dict[str, Any] | None, str | None]:
        if response.finish_reason == "length":
            return None, "finish_reason=length"
        if not response.response_text.strip():
            return None, "final content is empty"
        if validator is not None:
            validation = validator(response.response_text)
            if not validation.get("valid"):
                parse_error = validation.get("parse_error")
                if parse_error:
                    return None, f"malformed JSON: {parse_error}"
                failures = validation.get("validation_failures") or ["schema validation failed"]
                return None, "schema validation failed: " + "; ".join(str(item) for item in failures)
            parsed = validation.get("parsed")
            return parsed if isinstance(parsed, dict) else None, None
        try:
            parsed = json.loads(response.response_text)
        except json.JSONDecodeError as exc:
            return None, f"malformed JSON: {exc.msg} at character {exc.pos}"
        if not isinstance(parsed, dict):
            return None, "structured response must be a JSON object"
        return parsed, None

    attempts: list[ProviderAttempt] = []
    for index in range(max_recovery_attempts + 1):
        try:
            response = complete(prompt if index == 0 else prompt + "\n\nRECOVERY INSTRUCTION: return only a complete compact JSON object.")
        except ProviderError as exc:
            attempts.append(ProviderAttempt(
                index + 1,
                None,
                str(exc),
                None,
                physical_attempts=exc.physical_attempts,
                retryable=exc.retryable,
                http_status=exc.http_status,
            ))
            return StructuredProviderResult(False, None, None, "PROVIDER_ERROR", tuple(attempts))
        parsed, output_failure = assess(response)
        if output_failure is None:
            attempts.append(ProviderAttempt(index + 1, response, None, None))
            return StructuredProviderResult(True, parsed, response, None, tuple(attempts))
        retry_reason = output_failure if index < max_recovery_attempts else None
        attempts.append(ProviderAttempt(index + 1, response, None, output_failure, retry_reason))
        if retry_reason is None:
            return StructuredProviderResult(False, None, response, "PROVIDER_OUTPUT_ERROR", tuple(attempts))
    raise AssertionError("bounded recovery loop exhausted unexpectedly")


# Compatibility alias for callers written against the pre-amendment name.
OpenAICompatibleProvider = DirectProvider
