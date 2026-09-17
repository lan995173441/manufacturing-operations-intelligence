# Phase 09 — Deterministic KPI Engine

Status: completed. Authority: `docs/data/KPI_DEFINITIONS.md`, with `DATA_CONTRACT.md` and `ARCHITECTURE.md`.

- Implement the six supported KPIs in `domain.analytics`, with a shared production population, exact arithmetic, inclusive dates, line/shift scope, lineage, coverage and explicit unavailable states.
- Implement Completed Orders and Schedule Adherence as `unsupported_schema` results. The authoritative specification forbids inferring lifecycle events from slot quantities; hypothetical future examples cannot become current-schema numeric tests.
- Reuse domain validation for canonical records and integrity checks before filtering, so invalid or missing rows cannot disappear through a join or filter.
- Inventory uses the known material universe and latest observation at/before the end date, including carried-forward observations. Production line/shift filters do not narrow inventory.
- Use manually calculated fixtures for all eight functions: normal, boundary, missing data and applicable zero-denominator cases. For CO/SA these assert unsupported status, including zero-output/empty selections, rather than inventing lifecycle columns.
- Run `pytest tests/test_kpi.py -v`, `pytest -q`, and `ruff check .`; record exact results and archive the plan on success.

No database, UI, LLM, anomaly thresholds or authoritative formula changes are part of this task.

## Completion evidence

- `pytest tests/test_kpi.py -v`: 21 passed. Hand-calculated fixtures cover all eight candidates, supported KPI boundaries, invalid data, zero denominators, half-up display rounding, lineage, date/line/shift selection and as-of inventory coverage.
- `pytest -q`: 61 passed.
- `ruff check .`: All checks passed.
- Completed Orders and Schedule Adherence remain `unsupported_schema` under the current data contract; no quantity proxy or lifecycle field was invented.
- Product-owner decisions PO-01–PO-08 in KPI_DEFINITIONS remain pending; these implementation tests verify the documented draft semantics, not business approval.
