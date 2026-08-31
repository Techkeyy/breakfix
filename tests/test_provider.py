import json
import io
import os
import urllib.error
import unittest
from unittest.mock import patch

from breakfix.provider import (
    DirectProvider,
    ProviderError,
    ProviderResponse,
    bounded_structured_recovery,
)


def response(
    text: str,
    *,
    finish_reason: str = "stop",
    reasoning: str | None = None,
) -> ProviderResponse:
    return ProviderResponse(
        response_text=text,
        reasoning_text=reasoning,
        provider="deepseek",
        model="deepseek-v4-pro",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        latency_ms=1,
        monetary_cost_usd=0.01,
        finish_reason=finish_reason,
    )


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ProviderContractTests(unittest.TestCase):
    def test_deepseek_request_uses_json_mode_and_recovery_budget(self):
        with patch.dict(
            os.environ,
            {
                "BREAKFIX_PROVIDER": "deepseek",
                "BREAKFIX_DEEPSEEK_API_KEY": "test-only",
                "BREAKFIX_MAX_OUTPUT_TOKENS": "12000",
            },
            clear=True,
        ):
            provider = DirectProvider()
        body = provider._request_body("prompt", {"type": "json_object"})
        self.assertEqual(body["max_tokens"], 12000)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertNotIn("temperature", body)

    def test_deepseek_separates_reasoning_content_from_final_content(self):
        with patch.dict(
            os.environ,
            {"BREAKFIX_PROVIDER": "deepseek", "BREAKFIX_DEEPSEEK_API_KEY": "test-only"},
            clear=True,
        ):
            provider = DirectProvider()
        payload = {
            "model": "deepseek-v4-pro",
            "choices": [{
                "finish_reason": "stop",
                "message": {"reasoning_content": "private reasoning", "content": '{"ok":true}'},
            }],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        }
        with patch("urllib.request.urlopen", return_value=_FakeHttpResponse(payload)):
            result = provider.complete("prompt", response_format={"type": "json_object"})
        self.assertEqual(result.response_text, '{"ok":true}')
        self.assertEqual(result.reasoning_text, "private reasoning")
        self.assertEqual(result.response_format, "json_object")

    def test_deterministic_http_402_is_not_retried(self):
        with patch.dict(
            os.environ,
            {"BREAKFIX_PROVIDER": "deepseek", "BREAKFIX_DEEPSEEK_API_KEY": "test-only", "BREAKFIX_MAX_RETRIES": "2"},
            clear=True,
        ):
            provider = DirectProvider()

        def fail(_request, timeout):
            raise urllib.error.HTTPError(
                "https://api.deepseek.com/chat/completions",
                402,
                "payment required",
                {},
                io.BytesIO(b'{"error":{"message":"Insufficient Balance"}}'),
            )

        with patch("urllib.request.urlopen", side_effect=fail), patch("time.sleep") as sleep:
            with self.assertRaises(ProviderError) as raised:
                provider.complete("prompt")
        self.assertEqual(raised.exception.http_status, 402)
        self.assertFalse(raised.exception.retryable)
        self.assertEqual(raised.exception.physical_attempts, 1)
        self.assertEqual(raised.exception.retries, 0)
        sleep.assert_not_called()

    def test_transient_http_503_keeps_bounded_retry(self):
        with patch.dict(
            os.environ,
            {"BREAKFIX_PROVIDER": "deepseek", "BREAKFIX_DEEPSEEK_API_KEY": "test-only", "BREAKFIX_MAX_RETRIES": "2"},
            clear=True,
        ):
            provider = DirectProvider()
        calls = []

        def transient_then_success(request, timeout):
            calls.append(request)
            if len(calls) == 1:
                raise urllib.error.HTTPError(
                    "https://api.deepseek.com/chat/completions",
                    503,
                    "unavailable",
                    {},
                    io.BytesIO(b"temporary"),
                )
            return _FakeHttpResponse({
                "model": "deepseek-v4-pro",
                "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            })

        with patch("urllib.request.urlopen", side_effect=transient_then_success), patch("time.sleep"), patch("random.uniform", return_value=0):
            result = provider.complete("prompt")
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.retries, 1)
        self.assertEqual(result.physical_attempts, 2)

    def test_valid_structured_response(self):
        result = bounded_structured_recovery(lambda _prompt: response('{"ok": true}'), "prompt")
        self.assertTrue(result.success)
        self.assertEqual(result.parsed, {"ok": True})
        self.assertEqual(len(result.attempts), 1)

    def test_finish_length_recovery(self):
        calls = []
        outputs = iter([response("", finish_reason="length", reasoning="still thinking"), response('{"ok": true}')])
        result = bounded_structured_recovery(lambda prompt: (calls.append(prompt) or next(outputs)), "prompt")
        self.assertTrue(result.success)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.attempts[0].output_failure, "finish_reason=length")
        self.assertEqual(result.attempts[0].retry_reason, "finish_reason=length")

    def test_empty_content_recovery(self):
        outputs = iter([response(""), response('{"ok": true}')])
        result = bounded_structured_recovery(lambda _prompt: next(outputs), "prompt")
        self.assertTrue(result.success)
        self.assertEqual(result.attempts[0].output_failure, "final content is empty")

    def test_malformed_json_recovery(self):
        outputs = iter([response('{"ok":'), response('{"ok": true}')])
        result = bounded_structured_recovery(lambda _prompt: next(outputs), "prompt")
        self.assertTrue(result.success)
        self.assertIn("malformed JSON", result.attempts[0].output_failure)

    def test_schema_validation_recovery(self):
        outputs = iter([response('{"wrong": true}'), response('{"ok": true}')])
        validator = lambda text: {"valid": json.loads(text).get("ok") is True, "parsed": json.loads(text)}
        result = bounded_structured_recovery(lambda _prompt: next(outputs), "prompt", validator=validator)
        self.assertTrue(result.success)
        self.assertEqual(result.parsed, {"ok": True})

    def test_timeout_is_provider_error_and_is_not_retried_as_output(self):
        def timeout(_prompt):
            raise ProviderError("provider timeout", retries=2)

        result = bounded_structured_recovery(timeout, "prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_code, "PROVIDER_ERROR")
        self.assertEqual(len(result.attempts), 1)
        self.assertIn("timeout", result.attempts[0].provider_error)

    def test_api_error_is_provider_error_and_is_not_retried_as_output(self):
        def api_error(_prompt):
            raise ProviderError("provider HTTP 401", retries=2)

        result = bounded_structured_recovery(api_error, "prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_code, "PROVIDER_ERROR")
        self.assertEqual(result.output_contract_status, "PROVIDER_ERROR")
        self.assertEqual(len(result.attempts), 1)

    def test_recovery_exhaustion_is_explicit_and_bounded(self):
        calls = []
        result = bounded_structured_recovery(
            lambda prompt: (calls.append(prompt) or response("not json")),
            "prompt",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.failure_code, "PROVIDER_OUTPUT_ERROR")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result.attempts), 2)
        self.assertIsNone(result.attempts[-1].retry_reason)


if __name__ == "__main__":
    unittest.main()
