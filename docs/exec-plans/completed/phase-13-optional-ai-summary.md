# Phase 13 — Optional AI management summary

Status: completed. Chinese counterpart: [phase-13-optional-ai-summary.zh-CN.md](phase-13-optional-ai-summary.zh-CN.md).

Add an explicit, on-demand summary action in Reports & Insights. The application service reuses one validated report payload and projects only calculated KPI display values/status, bounded anomaly evidence, prepared daily trends, scope, and batch/definition identity. The provider receives no source rows or database access. One optional OpenAI Responses HTTP adapter uses environment settings, finite timeout/output limits, no response storage, and no new dependency. This provider selection is an implementation assumption for the explicitly requested optional feature; the callable boundary remains replaceable.

When disabled, keyless, timed out, failed, or malformed, return a labeled deterministic summary from the same facts. Reject malformed structure and unsupported numerical claims. Keep AI draft transient and invalidate it on batch, scope, or rule changes. Require human review; exports never trigger AI.

Verify with mocked provider and transport responses only, plus full pytest and Ruff. No live API calls in tests. Record final evidence and move paired plans to completed.

## Completion evidence and limits

- `Reports & Insights` now generates an on-demand summary through the application service. It labels AI drafts for human review or gives a deterministic offline result with a specific fallback status. The page cache is invalidated when batch, scope or anomaly threshold changes. Report exports remain independent of AI.
- The OpenAI Responses adapter sends only the bounded projection with `store=false`, a 12-second timeout and 650-token output limit. The environment uses `MOI_AI_ENABLED`, `MOI_AI_API_KEY` and `MOI_AI_MODEL`; no key is stored in settings, reports or UI state. The project does not auto-load `.env`.
- Malformed response structure and numerical tokens absent from the supplied facts are rejected. This mechanical check cannot establish the truth of causal or qualitative prose; management must review AI drafts. No live API request was made, so provider-account access and live model behavior remain unverified.
- `.venv/bin/pytest -q`: **124 passed in 34.93s**. `.venv/bin/ruff check .`: **all checks passed**. The 15 new tests use fake callables/HTTP responses and cover disabled/keyless operation, timeout/failure, malformed and unsupported output, identity mismatch, payload boundary, and offline UI generation.
- A final stricter check requires AI drafts to include limitations; after that focused change, `.venv/bin/pytest tests/test_management_summary.py -q` passed **15 tests** and Ruff passed again.
