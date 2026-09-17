# Phase 12 — Automated reporting

Status: completed. Chinese counterpart: [phase-12-automated-reporting.zh-CN.md](phase-12-automated-reporting.zh-CN.md).

Implement on-demand management exports for the existing local MVP. One application-service request reads one active batch, obtains existing analytics and anomaly results, and passes an immutable report payload to OpenPyXL and ReportLab renderers. Renderers do not query SQLite or recalculate KPIs. The UI prepares reports only on request and invalidates prepared downloads when the batch, filters or rule configuration change.

Excel: Overview, Production, Quality, Inventory, Anomalies, Data Quality and Summary worksheets, with final values, source/version information, full anomaly and inventory detail, and a prepared production chart. PDF: readable management sections, KPI and coverage states, production/quality charts based on prepared series, inventory risks, a capped anomaly preview with explicit truncation, batch/date/page labels, and a deterministic factual summary. Absent rules are labeled as unevaluated. Unsupported KPIs remain N/A. Workbook text from source-derived fields must be literal, not formulas.

Validation: temporary-directory integration tests inspect generated files, sections, source-backed values, stale state, empty scope, and a sample PDF rendering. Run the full regression suite and Ruff. Record evidence and move both plans to completed.

Assumption: the unapproved PRD suggestion of seven tabs and a 20-row PDF anomaly preview is used as a simple presentation cap for this MVP; it changes no business rule and is disclosed in the PDF. No AI provider or new KPI formula is introduced.

## Completion evidence

- A single service read produces one `ReportPayload` for both renderers. `Reports & Insights` prepares transient files only on request; batch/filter/rule changes invalidate old downloads.
- A sample run generated a 23 KB Excel workbook and a 31 KB, three-page PDF. Workbook inspection found the seven required sheets and two charts. All three PDF pages were rendered at review size and visually inspected; chart headings, tables, anomaly preview, footer and page numbers were legible. An initial orphan heading and fraction-form anomaly values were corrected before final review.
- `pytest tests/test_reporting.py -q`: six new report tests passed as part of the full suite. `pytest -q`: **109 passed in 24.65s**. `ruff check .`: all checks passed.
- Tests verify file signatures and nonempty sizes, section names, exact displayed KPI agreement with application-service analytics, complete Excel detail, labeled PDF truncation, empty/unconfigured states, formula-like source text, mismatched-result rejection and UI cache invalidation. They write generated files only to pytest temporary directories.
- No manufacturing formulas, anomaly rules, persistence semantics, or dependencies changed. Report layout remains an MVP presentation assumption, not a new approved business rule.
