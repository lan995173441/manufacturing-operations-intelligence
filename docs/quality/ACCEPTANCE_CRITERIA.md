# Manufacturing Operations Intelligence — Acceptance Criteria

Status: **engineering criteria drafted; product-owner acceptance pending** (2026-09-17). Chinese counterpart: [ACCEPTANCE_CRITERIA.zh-CN.md](ACCEPTANCE_CRITERIA.zh-CN.md). This document defines observable checks for the portfolio MVP; it does not approve provisional manufacturing semantics or declare client handover complete.

## Engineering acceptance checks

| ID | Required observable result | Evidence method |
| --- | --- | --- |
| AC-01 | Local startup listens on `127.0.0.1` only; the supported command and Streamlit configuration agree. | Start the documented command and inspect the listening socket. |
| AC-02 | One complete four-domain Excel workbook or four assigned CSV files is either accepted atomically or rejected with dataset, row, field, reason and severity. No invalid row is silently dropped. | Valid, mixed-invalid, sparse, dense and compressed-file fixtures. |
| AC-03 | Rejected input leaves the previous active batch intact; accepted replacement is readable after restart. Stored plan, actual and quality keys match, and a stored-content fingerprint mismatch causes a visible failure before filtered analytics. | Temporary SQLite integration tests, including deliberate orphan and tamper probes. |
| AC-04 | For every supported KPI, hand-calculated normal, boundary, missing-data and zero-denominator fixtures match the formulas in [KPI_DEFINITIONS](../data/KPI_DEFINITIONS.md). Completed Orders and Schedule Adherence remain labeled unavailable without lifecycle evidence. | Deterministic KPI tests and dashboard/report inspection. Passing tests verifies the *documented candidate formulas*, not their business approval. |
| AC-05 | Configured anomaly rules produce deterministic type, severity, entity, observed value, threshold, range and explanation. Strict boundary cases do not trigger; skipped checks remain visible. | Trigger, non-trigger, boundary and simultaneous-anomaly tests. |
| AC-06 | Five dashboard areas present the same selected batch and filters, show empty/unavailable states, and do not calculate KPIs in Streamlit code. | UI smoke tests and source review. |
| AC-07 | Excel and PDF reports use the same analytics payload; displayed KPI values match the engine. A long valid filter list paginates in PDF. Failure of one renderer leaves the other format downloadable. | Temporary-file report tests, long-scope PDF test and forced renderer-failure test. |
| AC-08 | Offline or failed AI requests leave the core app working with a deterministic summary. Accepted AI output can select only identified calculated facts; numeric text, causes or completion claims supplied by a model cannot enter the rendered narrative. Limitations are always deterministic. | Mocked provider tests, including unsupported fact and false-claim payloads; no live API call in unit tests. |
| AC-09 | `ruff check .` and `pytest -v` pass on the documented environment. Critical validation, KPI, anomaly, repository and report behaviors have focused tests. | Record command output and environment in the QA plan; do not substitute a global coverage percentage. |
| AC-10 | Portfolio assets use clearly labeled synthetic data, no secrets, and explain setup, data limitations and the five-area workflow. | Repository and README review. |

## Business acceptance gate — unresolved

The following decisions require a named product owner and date before claiming **client acceptance**. Tests cannot grant this approval. Record the decision in the owning document and reconcile dependent code/tests if the chosen meaning differs.

| Decision | Required ruling | Current implementation / document relationship |
| --- | --- | --- |
| BA-01 | Whether production attainment uses gross `actual_qty` or good output; whether pieces across products may be summed. | KPI-PA and KPI-OL use gross pieces under the draft KPI definitions. Product comparability is assumed only for the synthetic demo. |
| BA-02 | Whether `good_qty` and `scrap_qty` represent final disposition, and whether rejected/reworked units count as scrap. | KPI-GY and KPI-SR follow final good/scrap disposition; they are not first-pass yield or total rejection. |
| BA-03 | Meanings of production slot, planned time, runtime, unplanned line-minutes, inventory snapshot, safety stock and incomplete coverage. | Data Contract C02–C08 and KPI-TD/KPI-IR are provisional. |
| BA-04 | Anomaly thresholds, comparison boundaries, production-variance grain and severity. | Review PRD D06 and the implemented deterministic rule specification; no threshold is a manufacturing standard. The user selected per-slot absolute variance in the earlier anomaly task, but other business thresholds remain unapproved. |
| BA-05 | Treatment of Completed Orders and Schedule Adherence. | Current contract lacks completion/due evidence; both must remain unavailable unless a separately approved contract change supplies it. |
| BA-06 | Final intake, persistence, filter and report scope, including Excel/PDF versus charter Excel/HTML and inventory inclusion. | Later explicit feature tasks authorized the implementation; reconcile charter sections 6–10 with PRD D01–D05/D08–D10/D15 before client handover. |
| BA-07 | Performance target, workload, hardware and timing boundary. | Charter timing target and PRD D14 are unresolved; no benchmark is claimed here. |
| BA-08 | Whether optional AI output is part of client delivery and what human-review label is required. | AI is implemented as optional with offline fallback; see PRD D07 and ADR-003. |

The product owner should approve or amend BA-01–BA-08 in a dated decision record. Until then, the result is an engineering-validated **synthetic portfolio demonstration**, not an accepted manufacturing operating standard. Do not change authoritative definitions merely to pass an acceptance test.

## Charter–PRD reconciliation for review

Later explicit feature requests authorize the following *implemented demo behavior* but did not edit the original charter or approve its business assumptions. Review each row before handover; update the charter and PRD together only after a product decision.

| Topic | Original charter | Later requirement and demo | Decision needed |
| --- | --- | --- | --- |
| Input breadth | Single production-oriented template | Four domains and Excel/CSV | Confirm four-domain batch contract (PRD D01–D03/D10). |
| Inventory | Workflow excluded from charter MVP | Snapshot analytics and risk view | Confirm material-only as-of semantics (D04/D08). |
| Persistence | Local files preferred; database needs demonstrated need | SQLite active-batch replacement | Confirm atomic replacement and no history UI (D05). |
| Dashboard | One dashboard with a few production filters | Five navigation areas over one batch | Confirm navigation scope and inventory filter exception (D08). |
| Reports | Excel plus HTML; PDF excluded | Excel plus PDF; no HTML | Confirm format substitution (D09/D15). |
| Metrics | Five original production metrics | Eight candidates; two remain unavailable | Confirm approved definitions and whether unavailable cards meet release expectations (BA-01–BA-05). |
| Time/budget | 40–60 focused hours and an end-to-end timing target | Expanded feature set; no agreed benchmark | Re-estimate and define measurable workload/hardware (D11/D14). |
