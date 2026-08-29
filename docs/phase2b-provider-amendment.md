# Phase 2B provider amendment

Status: **frozen before the first Phase 2B provider call**  
Amendment date: 2026-08-29  
Parent frozen protocol: `73ac4e85f5839890142224eb82679431deb1b20b`

## Why this amendment exists

At amendment time, zero Phase 2B model calls had occurred and zero Phase 2B
results were known. The previously assumed OpenAI / `gpt-5.6-luna` direct
provider was unavailable because no authorized OpenAI API configuration existed
in the execution environment. The director confirmed that authorized DeepSeek
V4 Pro API access and credit are available for this benchmark. DeepSeek is
allowed because the official challenge does not require a particular provider.

The selected direct provider is therefore:

- Provider: `deepseek`
- Model: `deepseek-v4-pro`
- OpenAI-format base URL: `https://api.deepseek.com`
- Chat endpoint: `/chat/completions`
- Authentication variable: `BREAKFIX_DEEPSEEK_API_KEY`

## What remains unchanged

This amendment does not change the benchmark cases, hidden oracle, public
context, metrics, thresholds, deterministic three-experiment BreakFix budget,
fixed-matrix policy, evaluation logic, prompts, or PASS/FAIL gate. Both model
lanes use the same DeepSeek provider, model, and reasoning configuration. The
fixed matrix remains deterministic and does not call a model.

Only provider/model-specific request handling and telemetry configuration are
changed.

## Frozen reasoning configuration

DeepSeek V4 Pro is called with thinking mode enabled and `reasoning_effort` set
to `high` in both the generic comparator and BreakFix lanes. DeepSeek thinking
mode does not use temperature, so the request omits `temperature` for both
lanes. This is a single frozen setting, not a lane-specific tuning choice.

The request shape follows the official [DeepSeek Chat Completions
API](https://api-docs.deepseek.com/api/create-chat-completion/) and [thinking
mode guide](https://api-docs.deepseek.com/guides/thinking_mode/).

## Pricing and telemetry

Pricing was checked against the official [DeepSeek Models & Pricing
page](https://api-docs.deepseek.com/quick_start/pricing/) on 2026-08-29.
`deepseek-v4-pro` rates are recorded per 1 million tokens:

| Period | Cache-hit input | Cache-miss input | Output |
| --- | ---: | ---: | ---: |
| Off-peak | $0.022 | $0.66 | $1.98 |
| Peak | $0.044 | $1.32 | $3.96 |

Peak windows are 01:00-04:00 UTC and 06:00-10:00 UTC; all other times are
off-peak. Every response replay records the UTC request timestamp and selected
pricing period. The adapter uses provider-returned prompt-cache hit/miss
fields when present. If those fields are absent, it records
`unknown-conservative-miss` and prices all input tokens at the cache-miss rate.

Each replay records provider, exact model, request timestamp, latency, prompt,
cache-hit and cache-miss token counts when exposed, output and total tokens,
pricing metadata, retries, API errors, reasoning mode, and finish reason.

## Integrity statement

This amendment is committed before any DeepSeek request. The history-free
execution workspace, independent leakage audit, and local credential preflight
must pass before the first call. The API key remains local-only and is never
written to a trajectory, evidence file, or Git history.
