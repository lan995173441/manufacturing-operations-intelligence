# Manufacturing Operations Intelligence — Test Plan

Status: **RC1 engineering test plan** (2026-09-20). Chinese counterpart: [TEST_PLAN.zh-CN.md](TEST_PLAN.zh-CN.md).

This plan defines engineering evidence for the local synthetic-data MVP. It does not approve the provisional manufacturing semantics in the PRD, Data Contract, KPI Definitions, or BA-01–BA-08.

## Scope and release gate

The required evidence covers four-domain CSV/XLSX intake, validation and normalization, SQLite active-batch persistence, deterministic analytics and anomalies, five Streamlit areas, Excel/PDF reports, and optional AI summaries with offline fallback.

Release revalidation requires all targeted regression tests, `ruff check .`, and `pytest -q` to pass. UAT requires a separately dated product-owner disposition of BA-01–BA-08 and a performance workload/target; no test result can substitute for those decisions.

## Requirements-to-test traceability

| Requirement area | Primary automated evidence | Required manual/reconciliation evidence | Open limit |
|---|---|---|---|
| F01–F03 intake, validation, normalization | `tests/data/test_ingestion.py`, `tests/test_dashboard.py` | Preview selected file metadata and actionable diagnostics | Explicit encrypted-workbook fixture is pending |
| F04 persistence | `tests/data/test_repository.py`, `tests/test_application_service.py` | Restart and prior-active-batch preservation | Repository defense-in-depth hardening is tracked separately |
| F05 KPI calculations | `tests/test_kpi.py`, `tests/test_application_service.py` | Hand-calculate normal, boundary, empty, and zero-denominator examples | BA-01–BA-05 define business acceptance |
| F06 anomalies | `tests/test_anomalies.py`, `tests/test_dashboard.py` | Review rule/source evidence and strict threshold boundaries | BA-04 defines accepted thresholds/severity |
| F07–F10 dashboard | `tests/test_dashboard.py`, `tests/test_application_service.py` | Review all five areas with a valid, empty, and rejected upload | No accepted performance workload |
| F11–F12 reports | `tests/test_reporting.py` | Reconcile dashboard/service/Excel/PDF values; visually inspect long, empty, and full reports | Native Excel/Acrobat review is optional supplemental evidence |
| F13 optional AI | `tests/test_management_summary.py`, `tests/test_reporting.py` | Verify AI draft label and that regenerated reports use the current summary | No live-provider dependency in release tests |
| X01–X05 security, setup, reproducibility | `tests/test_smoke.py`, settings tests, lint, repository review | Clean install/startup and secret scan | Dependency versions are range-constrained, not locked |

## Test data and deterministic fixtures

| Fixture class | Coverage |
|---|---|
| Clean synthetic batch | 90 days, 3 lines, 2 shifts, 20 products, 40 materials; CSV and Excel paths |
| Validation failures | Missing domain, wrong headers/types, blank values, malformed CSV/XLSX, formula cells, merged cells, limits, duplicate normalized keys, invalid relationships |
| KPI fixtures | Weighted aggregation, line/shift/product/date filters, empty selection, zero denominator, zero output, over-100% attainment, inventory as-of/carry-forward/partial coverage |
| Anomaly fixtures | Trigger/non-trigger/equality boundaries, simultaneous matches, undefined ratios, missing inventory snapshots, filters |
| Report fixtures | Shared payload reconciliation, full anomaly list, 20-row PDF disclosure, stale payload/summary, long filter pagination, renderer isolation, formula-like source text |
| AI fixtures | Disabled/missing-key/failure/malformed/unsupported-claim fallback and valid mocked draft |

## Commands and recording

Run from the repository root on Python 3.12:

```sh
.venv/bin/ruff check .
.venv/bin/pytest -q
```

For a release revalidation, also run the affected modules first, generate reports from the clean synthetic batch, and compare the displayed values with the service payload. Record Python version, commit hash, command output, pass/fail/skip/warning counts, and any environment warning without suppressing it.

## UAT handoff conditions

Before UAT, attach this technical evidence and record the following outside the test suite:

1. Named product-owner decision and date for BA-01 through BA-08.
2. Approved workload, hardware boundary, and performance target for BA-07.
3. Immutable release identifier: package version `1.0.0rc1` and Git tag `v1.0.0-rc.1` on the revalidated commit.
4. A UAT result record identifying scenarios executed, expected results, actual results, and sign-off/defects.

Until items 1, 2, and 4 exist, this plan supports engineering revalidation only, not business UAT acceptance.
