# UI audit

Audit date: 2026-08-30

The hosted interface is a thin static Vercel frontend over the public BreakFix
API. The local Python evidence page remains available for saved runs.

## Checks

- Design-skill text audit: 0 long-dash errors, 0 small-text warnings.
- `GET /`: HTTP 200.
- `GET /api/runs`: HTTP 200.
- The final PASS run appears in both the page and API response.
- The final-summary index path is covered by `tests/test_web.py`.
- The page has explicit empty-state, card, heading, body, and chip styles and
  a responsive grid with a viewport meta tag.

- The deployed frontend was rendered and checked at 1440, 1024, 768, and 390px.
- The public browser flow reached `QUEUED`, `RUNNING`, and `COMPLETED` against
  the live API with real `CONFIRMED BREAK` evidence, assumptions, a targeted
  experiment, valid regression status, and the approval-gated fix entry point.
- Desktop and mobile screenshots were captured during the final review. The
  page remained free of horizontal overflow at all four widths.
