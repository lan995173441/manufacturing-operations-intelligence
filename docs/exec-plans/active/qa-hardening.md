# QA hardening — engineering audit

Status: completed QA pass, retained in `active/` as requested. Chinese counterpart: [qa-hardening.zh-CN.md](qa-hardening.zh-CN.md).

Feature development is frozen. Audit requirements, architecture, data contract, validation, KPI and anomaly rules, persistence, UI, reports, optional AI, error paths and documentation. Run repository Ruff and verbose pytest first; inspect business-critical test cases without targeting an arbitrary global coverage percentage. Classify evidence-backed findings as P0 blocker, P1 important or P2 improvement. Fix all P0 and P1 findings with clear portfolio value; defer cosmetic P2 work. Add focused regression tests for fixes, rerun the full validation suite and record exact evidence, remaining risks and documentation drift. No new product capabilities.

## Findings

| Priority | Finding and evidence | Disposition |
| --- | --- | --- |
| P0 blocker | None found in the audited local synthetic workflow. | No P0 fix required. This does not certify production use or settle business-rule approvals. |
| P1 important | XLSX parser scanned declared `max_row` before enforcing the row limit; a tiny sparse workbook with a far-out cell could stall import. | Reject declared worksheet dimensions above 10,001 rows or 100 columns before scanning. Added a sparse-workbook regression test and documented the parser guard in both Data Contract versions. |
| P1 important | Report payload verification checked only batch ID and filters; session caches keyed no KPI definition/fingerprint identity. A stale calculated result could be reused after a definition change. | Verify each report KPI ID, batch, fingerprint, contract, definition and scope. Include fingerprint, contract, KPI/rule versions, scope and threshold in transient report/summary cache keys. Added stale-fingerprint and cache-invalidation tests. |
| P1 important | An incompatible or corrupt SQLite file produced an uncaught dashboard exception. Sample-file read failure was also raw I/O. | Translate repository/SQLite failures at the service boundary and show actionable dashboard errors without resetting data; label unreadable sample files. Tested wrong schema version and corrupt bytes. |
| P1 important | No local setup/walkthrough guide; V0/ADR/PRD/architecture text could be mistaken for current missing-file or AI status. | Added bilingual README, paired historical-status notes, and this QA record. Preserved unresolved product-owner assumptions. |
| P2 improvement | Deterministic summary wording and anomaly number formatting are duplicated in report and optional-summary modules. | Deferred: current outputs agree; consolidating them now would create unrelated refactor risk. |
| P2 improvement | Ninety daily observations make static PDF charts dense; UI/quality release documents and AGENTS V1 are still not finalized. | Deferred: three-page sample PDF remains readable; future release planning and product-owner decisions are separate from this frozen-feature QA task. |

No additional functional defect, architecture violation, or dead code was confirmed. Pure domain modules have no Streamlit, SQLite or provider imports; report rendering has no SQL or KPI calculation. The UI calls application services for analytics, anomaly and report work. The original charter/PRD business differences and missing order-lifecycle evidence remain explicitly unresolved; the audit did not silently change formulas or claim approval.

## Business-critical test review

- Validation/ingestion (`domain/validation.py`, `data/readers.py`, `services/ingestion.py`): Excel/CSV equivalence, type and missing-field errors, duplicates, cross-domain relationships, source locations, malformed/partial input, and the new sparse-dimension limit. Invalid batches remain inactive.
- KPI engine (`domain/analytics.py`): hand-calculated examples, exact fractions and display rounding, zero denominators, empty/filter boundaries, invalid canonical data, inventory as-of/partial coverage, and explicitly unsupported order-lifecycle KPIs.
- Anomaly engine (`domain/anomalies.py`): all five triggers, exact thresholds, simultaneous rules, zero/skip cases, partial inventory, invalid batch, and configuration/severity validation.
- Reports (`reporting/renderers.py`): Excel/PDF signatures and sections, KPI agreement with the service, complete Excel anomaly detail, PDF preview labeling, empty/unconfigured states, literal-string safety, stale-result rejection and transient download invalidation. A new full-scope synthetic PDF was rendered and all three pages visually reviewed: labels, charts, repeated anomaly header, page numbers and summary were readable; no clipping or overlap found.
- SQLite, dashboard and AI boundaries: integration tests cover replacement/rollback, restart and filters; all five UI areas and corrupt database errors; AI disabled/keyless/timeout/failure/malformed/unsupported output with fake providers. Unit tests make no external API call.

This review is based on behavior and edge-case evidence, not an arbitrary global coverage target. `pytest-cov` is not installed; no numerical coverage percentage is claimed.

## Validation evidence

Baseline: `ruff check .` passed; `pytest -v` passed **124 tests in 36.15s**. After fixes, targeted validation suites passed. Final full run: `ruff check .` **all checks passed**; `pytest -v` **127 passed in 26.56s** on Python 3.12.2. No new product capability, dependency, KPI formula or anomaly threshold was introduced. Temporary PDF QA artifacts were removed.
