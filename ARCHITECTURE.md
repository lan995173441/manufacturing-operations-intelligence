# Manufacturing Operations Intelligence — Architecture

Date: 2026-09-15  
Status: Design proposal for review; technology constraints supplied by the user are binding. No implementation is authorized by this document.  
Chinese counterpart: [ARCHITECTURE.zh-CN.md](ARCHITECTURE.zh-CN.md)

QA status (2026-09-17): This is the original design record. Later explicit feature tasks implemented the local MVP; statements below about missing future documents or absent implementation describe the design date. The QA findings and remaining decisions are tracked in [qa-hardening](docs/exec-plans/active/qa-hardening.md).

## 1. Basis, decisions, and unresolved requirements

Read [AGENTS V0](AGENTS.md), [Project Charter](docs/product/PROJECT_CHARTER.md), [PRD](docs/product/PRD.md), and [User Stories](docs/product/USER_STORIES.md). This design covers PRD MUST capabilities F01–F12 and provides an isolated optional extension for F13. It does not promote S01/S02/C01 into required features.

The user now specifies Python, Streamlit, Pandas, Plotly, SQLite, OpenPyXL, and ReportLab. These choices resolve the previously undecided stack and database technology, not the business meaning of persisted data. The architecture below is a proposed organization of that stack, not approval of every PRD assumption.

The Data Contract, KPI Definitions, UI Spec, Test Plan, and Acceptance Criteria remain missing future sources of truth. They must settle field definitions, business keys, formulas, thresholds, inventory semantics, filters, layouts, and release gates. No manufacturing formula, table DDL, or numeric anomaly threshold is defined here.

| Existing difference / open decision | Architectural treatment |
| --- | --- |
| Charter: Excel-only input, one worksheet; later requirements: Excel/CSV and four domains | Provide file readers for both formats. Exact workbook/file packaging remains D01/D10. |
| Charter excludes inventory and PDF; later requests require them | Include Inventory and PDF boundaries, explicitly following the later requests. Do not claim the charter has been reconciled. |
| One dashboard versus five areas | One application with five thin views; no independent applications or role systems. |
| PRD says database technology is undecided | SQLite is now an explicit user constraint; replacement/merge policy D05 remains open. |
| PRD/AGENTS inventories say Architecture is missing | Historical V0 inventories predate this artifact. This document now exists; no V1 upgrade or broad document rewrite is performed here. |
| D02–D06/D08: grains, completeness, inventory, import identity, rules, filters | Isolate these decisions in data validation/domain logic. Do not choose defaults during implementation before they are documented. |
| D07: optional AI delivery | Core is complete without AI. Provider choice and delivery priority remain separate from this integration boundary. |
| D09/D11/D14/D15: HTML, effort, performance, report layout | Design required Excel/PDF only; HTML retention is unresolved. Do not assert the old effort/performance estimates or draft sheet/page limits are approved. |

Related decisions: [ADR-001](docs/decisions/ADR-001-tech-stack.md), [ADR-002](docs/decisions/ADR-002-database.md), [ADR-003](docs/decisions/ADR-003-ai-boundary.md).

## 2. System context and runtime

A single analyst uses a local browser to operate one Streamlit Python process. Synthetic Excel/CSV files enter the application; normalized records and import provenance persist in one local SQLite database. The browser shows analytics and downloads generated Excel/PDF files. An external model is contacted only through an explicit optional summary request.

There is no separate web API, frontend server, database server, task queue, scheduler, authentication, or cloud platform. Operations are synchronous and user-triggered. SQLite is durable state; Streamlit session state holds temporary selections and view results, not the only copy of imported records. Session state is associated with a user session, which is why restart recovery must use persistence. [Streamlit session-state documentation](https://docs.streamlit.io/develop/concepts/architecture/session-state)

Single-user local operation is the charter baseline, not a claim of secure public hosting or concurrent team support. Bind local operation to the local machine; deployment outside that context requires a separate scope/security decision. No performance capacity is claimed before measurement.

## 3. ASCII architecture diagram

```text
                     Analyst / local browser
                              |
 +-------------------------------------------------------------+
 | UI: Streamlit                                                |
 | Overview | Production | Quality | Inventory | Reports        |
 | Plotly displays result tables; no business calculations      |
 +----------------------------+--------------------------------+
                              v
 +-------------------------------------------------------------+
 | Application / Service Layer                                 |
 | import | analyze | export | optional summarize               |
 | Owns workflow, result identity, error translation            |
 +----------------------------+--------------------------------+
                              v
 +-------------------------------------------------------------+
 | Domain Analytics                                            |
 | validate | normalize | select/join | KPIs | rule anomalies    |
 | Pure Python/Pandas functions; structured analytics result    |
 +----------------------------+--------------------------------+
                              v
 +-------------------------------------------------------------+
 | Data / Repository Layer                                     |
 | Excel/CSV readers | one concrete SQLite repository           |
 | Stored normalized records + provenance; no KPI SQL           |
 +----------------------------+--------------------------------+
                              |
                        Local SQLite file

 Service also calls lower data modules directly for I/O.
 The vertical arrows show allowed downward dependency direction,
 not a requirement that pure analytics call the repository.

 Service -> validated result -> Excel renderer (OpenPyXL) -> XLSX
                            +-> PDF renderer (ReportLab) -> PDF
                            +-> optional AI adapter -> external LLM
                                      |
                             labeled draft or fallback
```

Reporting and AI are service-invoked output adapters, not additional business layers. Uploads enter through UI and service into the readers; the service passes parsed records to domain validation. Results travel back up to UI.

## 4. Major modules and responsibilities

Names below are proposed logical modules, not files created by this task. Use ordinary modules/functions; split files only when responsibilities or readability justify it.

| Module / layer | Responsibility | Must not do |
| --- | --- | --- |
| `ui` — UI | Navigation for all five areas, upload widgets, filters, diagnostic display, Plotly figures, downloads | SQL, business joins, KPI aggregation, anomaly decisions, direct model calls |
| `services` — Application | Coordinate import, analysis, report export and optional summary; resolve current dataset identity; return explicit outcomes | Duplicate formulas, implement schemas, render Streamlit controls |
| `domain.validation` — Domain | Schema/value/relationship checks specified by the future Data Contract; validation issues with locations | Read files, silently repair operational values, choose undocumented rules |
| `domain.normalization` — Domain | Documented conversions and transformations, preserve source references, post-conversion validation | Unapproved imputation or dropping invalid rows |
| `domain.analytics` — Domain | Applicable selection, joins, KPI values, trend/comparison tables, inventory calculations, deterministic anomaly rules | Depend on Streamlit, SQL, reports, model providers, network, or filesystem |
| `data.readers` — Data | Decode Excel/CSV into candidate records; preserve source names/locations and identifiers; report parse failures | Declare data business-valid or calculate metrics |
| `data.repository` — Data | One concrete SQLite repository; connections, consistent reads, atomic writes, provenance, schema-version checks | Streamlit state, report formatting, business KPI calculations in SQL |
| `reporting` — Output adapter | OpenPyXL and ReportLab renderers consume the same analysis result; presentation formatting and pagination | Load database records or recompute business metrics |
| `summaries` — Optional output adapter | Deterministic text from results; optional provider request from selected aggregate facts; labeled outcomes | Write source/database data or become a prerequisite for analytics/reporting |

A small set of standard Python records may describe validation issues, validated batches, analysis results, and summary outcomes. Keep these beside their owning layer. Do not build a universal data-transfer framework or a shared miscellaneous utility package.

### Five application areas

- **Overview (F07):** Display service-supplied summary metrics, trends, coverage, and anomaly summaries.
- **Production (F08):** Display supplied plan/actual comparisons, production trends, and source-backed exceptions.
- **Quality (F09):** Display supplied quality measures, trends, and exception evidence.
- **Inventory (F10):** Display supplied inventory measures and coverage; exact snapshot/filter semantics remain D04/D08.
- **Reports & Insights (F11/F12, optional F13):** Preview explicit report scope, request Excel/PDF, and optionally request a labeled AI draft.

Plotly receives already calculated series. Pages may arrange columns, set labels, or paginate for display; operations that change metric populations, totals, rates, business ranking, or anomaly membership belong in analytics. Navigation need not correspond to five physical page files.

## 5. Dependency direction and boundary contracts

Required conceptual layering is **UI → Application / Service → Domain Analytics → Data / Repository**. No lower layer imports UI or services. A higher layer may call a lower layer directly when appropriate: services perform I/O through Data and pass returned records to pure Domain functions. Domain need not depend on Data at all. This avoids a repository call hidden inside a KPI function while preserving downward-only dependencies.

| Caller | Permitted dependencies |
| --- | --- |
| UI | Services, Streamlit, Plotly, presentation-only formatting |
| Services | Domain, concrete Data modules, reporting, summaries |
| Domain | Python standard library and Pandas; no I/O adapters |
| Data | Python `sqlite3`/file facilities, Pandas/OpenPyXL for parsing; no upper-layer imports |
| Reporting | Standard library, OpenPyXL/ReportLab, result record definitions only |
| Summaries | Standard library, result definitions, optional isolated provider transport |

Boundary records carry data, not active database connections or Streamlit objects:

- **Candidate records:** decoded source values and location references; not yet trusted.
- **Validation outcome / validated batch:** explicit issues, allowed transformation log, contract version, and accepted normalized records. Only a successful outcome may be committed.
- **Analysis request:** dataset identity and explicit scope. Domain resolves business selection according to approved definitions.
- **Analytics result:** metrics, prepared chart/detail tables, anomaly evidence, validation/coverage status, source references, dataset identity, effective filters, and contract/KPI/rule versions. No renderer invents missing values.
- **Summary outcome:** draft/fallback/unavailable status, text, and the identity of its originating analytics result.

These are conceptual payloads, not finalized schemas. A result is treated as read-only: do not mutate shared Pandas frames in UI/renderers. Use local display copies where needed. No serialization protocol, generic repository interface, dependency-injection container, or event bus is required.

## 6. Data flow and Streamlit reruns

1. **Receive:** UI collects file bytes and intended domains; an explicit import action calls the service. Uploading alone does not replace accepted data.
2. **Parse:** readers decode inputs without losing source positions. Do not rely on automatic type inference where it would destroy identifier meaning. Supported packaging and limits follow the future Data Contract.
3. **Validate and transform:** domain checks candidates, performs only approved conversions, then validates normalized keys and relationships. Distinguish empty, invalid and zero values under the approved contract. Invalid input remains visible as diagnostics.
4. **Persist:** service submits a successful batch to the repository. Commit all affected records and metadata in one transaction. Complete-batch replacement is a proposal under D01/D03/D05, not a business rule finalized here.
5. **Read consistently:** service loads normalized records and dataset identity within one coherent database read, then closes the connection before calculation. Never combine domains read from different active datasets.
6. **Calculate:** domain creates metrics, prepared view tables, coverage and anomaly evidence once for the requested scope. Record definition versions and source identity in the result.
7. **Display:** service returns the result; five views render appropriate sections. Expected no-data and unavailable cases are explicit.
8. **Export:** export service verifies result identity/scope and supplies the same result to both renderers. If report scope differs from a page's local selection, obtain a new result via the analysis service and disclose that scope; renderers do not filter/recalculate metrics themselves.
9. **Optional narrative:** on explicit request, summarize the current structured result. Regenerating reports may attach that matched narrative; reporting itself does not call a model.

Keep temporary upload state, filters, and the last result in the current UI session. Streamlit reruns must not automatically re-import, re-export, or call AI. Expensive side effects require explicit actions. Before reuse/export, check the result's dataset and definition versions and effective filters. On mismatch, discard the cached view/summary and obtain a fresh result. If a batch commits after a result is created, an export must either use a verified, explicitly identified snapshot or refresh before publication; never label old values as the new dataset.

Start without cross-session caching, cached shared database connections, or a worker queue. A fresh analysis can be recomputed by the service when needed; “no recalculation in reports” means no independent metric implementation in renderers, not a ban on calling the analysis service for a changed scope.

## 7. Persistence approach

Use a single local SQLite file through Python's `sqlite3`, with one concrete repository. SQLite does not need a separate database server; this matches the local MVP. Parameterized queries and explicitly controlled transactions are required. [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html)

Persist normalized records for the four required domains, source/validation/normalization provenance necessary to explain accepted data, dataset identity, and schema/contract version metadata. Exact tables, columns, constraints, and key relationships await the Data Contract. Do not use SQLite's permissive value handling as a substitute for domain validation.

For the proposed replacement policy, normalize outside the write transaction, then replace affected records and update active identity together inside it. Roll back on any failure. Confirm the prior dataset is still active before describing the import as failed; if commit outcome is uncertain, reopen and inspect identity rather than automatically submitting the batch again. Re-import identity/comparison semantics remain D05; transaction safety does not settle that policy.

Use short-lived connections per operation, closed in all paths. Do not hold a transaction during chart rendering, file generation, or network calls. Handle lock/busy errors with a bounded wait and an explicit retryable message. No global connection shared across Streamlit sessions, no server database, ORM, or connection pool.

Read all required domains under one read snapshot. Keep repository SQL focused on persistence and retrieval, not KPI joins, aggregates, or anomaly thresholds; domain owns business selection and calculation. A schema-version mismatch blocks normal access with a clear upgrade message; do not silently drop/recreate or reinterpret an existing database. Initial schema setup and later small explicit migrations belong to a future implementation task, not a migration framework now.

Do not persist derived KPIs as a second source of truth. Recompute them from accepted records and versioned definitions. Generated reports/AI drafts may remain transient; after restart the normalized dataset is retained but prior view results need recomputation. Raw input files stay untouched; do not archive their full contents or rejected batches in SQLite by default. Provenance is not a promise of source-file retention or enterprise auditing.

## 8. Error handling strategy

| Failure | Owner and response | State guarantee |
| --- | --- | --- |
| Corrupt/unsupported file | Reader returns parse error; service adds domain/file context | No accepted data change |
| Schema/value/relationship failure | Domain returns structured issues with available row/field evidence | No silently dropped rows; no rejected batch activated |
| Database lock/write failure | Repository rolls back; service reports retryable or recovery-required outcome | Prior committed data remains authoritative; uncertain outcomes are inspected |
| Missing/incompatible definition or schema | Service blocks dependent operation and identifies missing source/version | No guessed rules or destructive automatic reset |
| Empty data or unavailable metric | Domain returns explicit status and coverage | No fabricated metric value |
| Unexpected analytics exception | Service fails analysis visibly and records safe diagnostic context | No partial result presented as complete; accepted source data remains intact |
| Excel/PDF rendering failure | Export service returns format-specific failure | No partial download; database and other completed artifacts unchanged |
| AI disabled/failure/unusable reply | Summary adapter returns labeled fallback or unavailable status | Core analytics and reports remain available |

Do not catch all exceptions and continue with empty tables. Keep expected validation outcomes separate from unexpected failures. Standard Python logging is sufficient; log an operation reference, category, and sanitized diagnostic context. Never log API keys, connection secrets, full uploaded data, or full model payloads. UI receives useful recovery guidance rather than raw stack traces.

## 9. Reporting architecture

One report service accepts a validated Analytics result and optional matching Summary outcome. It passes the same computed numbers, tables, definitions, scope and evidence to two format-specific functions:

- **Excel:** OpenPyXL writes final values, labels, units and provenance into the approved workbook layout. It does not embed business formulas as a second calculation engine. Treat source-derived strings as literal data rather than executable spreadsheet formulas.
- **PDF:** ReportLab handles page layout, tables, page numbers and simple vector charts using prepared series from the result. Use ReportLab chart/drawing primitives rather than exporting Plotly images. This avoids adding Kaleido, a browser runtime, or an image conversion pipeline solely for PDF output. ReportLab provides document layout and graphics facilities. [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)

Plotly is for interactive UI; ReportLab is for static report rendering. Different visual renderers may format the same series differently, but cannot change its values. Renderers may wrap text, paginate, or apply approved detail truncation with disclosure; they must not calculate totals or rates from raw rows. Exact charts, sheets, fonts, languages, and truncation limits remain UI_SPEC/Acceptance Criteria decisions under D15.

Generate complete bytes in memory for this bounded local workflow, then expose the download only on success. Measure memory alongside file limits before implementation acceptance. No report database, scheduler, email delivery, HTML export subsystem, or artifact store is added. Report generation never needs AI connectivity and never mutates persisted data.

## 10. Optional AI boundary

The analysis service produces authoritative structured results without AI. A summary service constructs an allowlisted aggregate fact payload from that result: identifiers for reported facts, displayed values/units, approved comparisons, anomaly evidence summaries, scope and limitations. Do not send raw input rows, files, database access, or credentials in the prompt.

A single optional provider adapter may turn this payload into a human-review draft. Provider/model/SDK are not selected in this task. If later enabled, load configuration only on explicit request, use environment secrets, enforce a bounded timeout/output size, and avoid automatic retry loops. No tool calling, autonomous actions, or multi-provider framework.

Provide deterministic management text from existing result fields as the offline path. Disabled AI, absent key, provider error, or rejected output returns that fallback or an explicit unavailable narrative; never block metric/report access. Summary output carries its result identity and is invalidated when dataset, scope, or definitions change.

Validate response structure and check claims against the fact payload where mechanically possible; reject unsupported numerical claims rather than insert them into a report. Such checks do not prove narrative correctness or causality: require human review and evaluate representative scenarios. AI cannot alter records, rules, thresholds, calculations, or compliance decisions. See [ADR-003](docs/decisions/ADR-003-ai-boundary.md).

## 11. Testing architecture and MUST coverage

Tests call ordinary functions and service entry points without starting Streamlit wherever possible. Use temporary files/databases and synthetic fixtures. Python's standard test facilities are sufficient initially; framework/lint commands are left to TEST_PLAN and AGENTS V1. No test code is created here.

| Boundary / requirement | Planned evidence |
| --- | --- |
| Readers + domain validation, F01–F03 | Equivalent supported Excel/CSV fixtures; corrupt files, missing/invalid fields, identifier preservation, normalization collisions, source locations. Expected outcomes come from approved Data Contract. |
| Repository + services, F04 | Temporary on-disk SQLite, close/reopen recovery, all-or-nothing commit and injected failure, lock handling, schema mismatch; approved re-import/replacement behavior. Use disk, not only in-memory tests, for restart evidence. |
| Pure analytics, F05–F06 | Independently derived fixtures for approved definitions, missing/zero cases, grouping, inventory populations, anomaly boundaries and skipped checks. Expected values must not be generated by the code under test. |
| UI/service boundary, F07–F10 | Each area's values trace to result fields; navigation/filter/no-data checks; import side effects do not repeat on rerun; no page-level formulas or database calls. |
| Report adapters, F11–F12 | One result rendered into both formats; OpenPyXL read-back of Excel values and literal text safety; PDF visual review for clipping, page breaks, labels and matching facts. Report tests use supplied result fixtures, not repository reads. |
| Optional AI, F13 | Disabled/missing-key/timeout/malformed/unsupported-claim outcomes using a fake provider; identity invalidation and core export with provider absent. A live-model call is not required for core tests. |
| Integrated offline workflow, F01–F12 | Accepted input → persistent normalized data → metrics/anomalies → five areas → Excel/PDF; invalid import leaves prior dataset identified and usable. |
| Dependency rules | Small import/dependency checks or focused review verify that Domain has no UI/I/O imports and report modules contain no business calculations or repository calls. No architecture enforcement framework. |

Future TEST_PLAN defines procedures; ACCEPTANCE_CRITERIA defines release gates. Test time, memory and output readability against the approved workload rather than silently adopting unresolved PRD timing targets. Do not change business definitions to make tests pass.

## 12. Abstraction necessity review

| Proposed abstraction | Keep? | Necessity / simpler boundary |
| --- | --- | --- |
| Five UI views | Yes | Required areas; ordinary functions are sufficient, not five services. |
| Application services | Yes | Prevent UI from owning transactions, calculations and side effects; one module can start the workflow. |
| Pure validation/normalization/analytics | Yes | Independent correctness tests and one business-rule implementation; no domain class hierarchy. |
| One concrete repository | Yes | Centralize SQLite transactions and consistent reads; no generic repository or ORM. |
| Excel/CSV reader functions | Yes | Distinct decoding needs; no universal importer or plugin registry. |
| Small boundary/result records | Yes | Preserve validation status and result identity across consumers; no schema framework. |
| Two report renderers | Yes | Required formats need different presentation tools; no template engine or shared chart abstraction. |
| One optional summary adapter | Only if AI is delivered | Contains network/config failures; simple callable suffices, no agent/provider framework. |
| Deterministic summary function | Yes, as the proposed offline report path | Uses already calculated fields; no separate intelligence engine. |
| Standard config/logging | Yes, small functions | Local paths and safe diagnostics; no configuration service or observability platform. |
| Global cache, report store, worker queue | No | Not needed for current synchronous bounded scope; measure before proposing exceptions. |
| API server, DI container, event bus, ORM, microservices | No | Add setup and indirection without solving a required MVP problem. |

Architecture is complete as a reviewable design, not as implemented software. Before business implementation, resolve the owning data/KPI/UI/quality documents, reconcile outstanding product conflicts, and review AGENTS V1. Do not automatically start those phases.
