# QA review remediation

Status: active. Chinese counterpart: [qa-review-remediation.zh-CN.md](qa-review-remediation.zh-CN.md).

Address the reviewer-reproduced blocker and five high-severity defects without adding unrelated product scope. Preserve explicit product-owner approval gates for manufacturing semantics. Add a bilingual acceptance document with measurable engineering checks and marked pending business decisions. Harden loopback startup, persisted-batch verification, AI fact grounding, XLSX resource limits, and report export isolation. Reproduce each defect in regression tests; run Ruff and the complete pytest suite, inspect PDF layout, and record remaining limits.

## Engineering outcome (2026-09-17)

- Drafted paired [acceptance criteria](../../quality/ACCEPTANCE_CRITERIA.md) with ten measurable engineering checks, eight explicit business approval gates and a charter–PRD reconciliation table. **Client acceptance remains pending**; no product owner has approved candidate manufacturing semantics or the scope reconciliation.
- Pinned Streamlit to loopback in repository configuration and both supported launch commands. A local process listened only on `127.0.0.1:8765`; `/_stcore/health` returned HTTP 200. The test process was stopped.
- Full active-batch reads now load every canonical table independently, reject mismatched production keys/source references and verify a stored-content fingerprint before filtered analytics. Orphan and tamper probes are regression tests.
- AI responses can select only allowlisted fact IDs; the program supplies metric labels/numbers and mandatory limitations. Free-form false metric, equipment-cause and order-completion claims trigger fallback.
- XLSX archive expansion, entry count and populated cell count are bounded before openpyxl; sheets stream in read-only mode. Sparse, dense and highly compressed cases are covered.
- PDF scope IDs occupy bounded, splittable rows. A 500-ID PDF test succeeds; the long-scope document shrank from 18 to 5 pages after grouping short IDs. Rendered pages 1, 3 and 5 were visually checked for legible filters, KPI table, charts and concluding sections. Either report format remains available when the other renderer fails.

Final validation: Python 3.12.2; `.venv/bin/ruff check .` **passed**; `.venv/bin/pytest -v` **135 passed in 38.38s** before the final PDF pagination refinement, followed by `.venv/bin/pytest -q` **135 passed in 45.17s** after it. No manufacturing KPI formula, anomaly threshold or product capability was changed.

## Remaining gate

Product-owner decisions BA-01–BA-08 in the acceptance document must be dated and reconciled with the charter/PRD before handover as accepted operational intelligence. Keep this plan active until that external decision is recorded; engineering remediation is complete.
