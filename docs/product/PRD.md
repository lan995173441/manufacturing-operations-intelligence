# Manufacturing Operations Intelligence — Product Requirements

QA status (2026-09-17): This is the original requirements draft. Later explicit user tasks delivered F13 as an optional implementation and authorized the named technology stack. Historical "missing document" and AI-priority statements below do not describe current repository contents or retract the still-open product-owner business decisions. See [qa-hardening](../exec-plans/active/qa-hardening.md).

Date: 2026-09-15  
Status: V0-aligned requirements draft; awaiting review, not implementation approval  
Companion: USER_STORIES.md; Chinese counterpart: PRD.zh-CN.md

## 1. Purpose, audience, and authority

Create a portfolio MVP demonstrating how manufacturing spreadsheets become trustworthy operational analytics and management reports. Primary users are manufacturing analysts, production supervisors, quality and inventory staff, and operations managers. Upwork clients and prospective employers evaluate the complete workflow and its engineering evidence.

The project remains a single-user, local application for one fictional factory, not a production MES. Only requirements documentation is authorized in this task.

Read [AGENTS.md](../../AGENTS.md) V0 before acting on this draft. The project charter and user stories exist; Architecture, Data Contract, KPI Definitions, UI Spec, Test Plan, Acceptance Criteria, and execution plans do not yet exist. Their absence is not permission to invent final decisions. The charter remains unchanged.

**Authority and status:** The user explicitly requested four domains, five areas, Excel/CSV intake, validation, normalization, persistence, deterministic KPIs/anomalies, Excel/PDF reporting, and optional AI summaries. These capability requests guide this PRD. Specific import policies, formulas, thresholds, inventory semantics, layouts, performance limits, and AI delivery priority remain proposals. MUST labels do not approve those details. No framework, database, module structure, or implementation plan is selected here.

**Conflict register — open for documented reconciliation:** The following differences are surfaced, not silently resolved. The latest user request establishes the newly requested capabilities, but does not approve every detail proposed in the earlier PRD. Before implementation, reconcile the charter and relevant owning documents; do not change business behavior based on this table alone.

| Charter baseline | Later request / unresolved reconciliation |
| --- | --- |
| One worksheet, Excel only | Four input domains; Excel and CSV support. |
| Local files without required persistence | Normalized records must persist across application restarts. Storage technology is undecided. |
| One dashboard | Five areas within one application, sharing calculations and filters. |
| Inventory excluded | Inventory analytics requested. Snapshot-only semantics are proposed under D04, not approved. |
| Five KPI examples, anomaly models excluded | Rule-based anomalies requested; this does not require a learned model. Inventory metric definitions and thresholds remain undecided. |
| Excel and HTML reports; PDF excluded | Excel/PDF explicitly requested. Replacing HTML rather than keeping a third format is a proposal awaiting D09. |

The earlier PRD also treated optional AI delivery as MUST and split the charter's end-to-end timing target into separate limits. Neither interpretation was explicitly approved; D07/D14 remain open.

The charter's 40–60-hour estimate is not validated for this expanded scope. Re-estimate before implementation; do not silently reduce required domains or capabilities to preserve that estimate.

## 2. Priority and product boundary

- **MUST:** Core capabilities F01–F12: four domains, five areas, Excel/CSV intake, validation, normalization, persistence, deterministic KPIs/anomalies, and Excel/PDF reporting. The core must work without an AI API key. Their detailed clauses remain draft where they depend on open decisions.
- **SHOULD — proposed, not additional approved scope:** Downloadable guidance (S01) and basic keyboard/table accessibility (S02).
- **COULD — proposed:** Optional AI summary F13; its release commitment remains open under D07. Prior-period comparison C01 is an unapproved candidate, not a delivery promise. Do not implement these solely because they appear here.
- **OUT OF SCOPE:** MES execution, scheduling, inventory movements or write-back, purchasing, stock valuation, multi-site/multi-user services, authentication, live integrations, arbitrary column mapping, forecasting, statistical/ML anomaly models, configurable rule builders, chatbot/agents, automated email, report scheduling, PowerPoint export, mandatory hosting, and enterprise infrastructure.

## 3. Core workflow and state

Manufacturing spreadsheet files → data validation → cleaning/transformation → persistence → KPI calculation → rule-based anomaly detection → dashboard → automated reports → optional AI management summary.

**Proposed transaction behavior (D01/D03/D05):** Upload an entire batch, validate structure and values, perform only permitted normalization, and recheck normalized relationships before committing. A batch is either rejected with diagnostics or accepted in full. Acceptance activates the new dataset only after a successful durable write. Failed imports leave the previous active dataset intact and visibly identified. Users never see failed input mixed with previous results.

Reports are generated on demand without manual assembly. **Proposed summary behavior (D07):** Initial reports include a deterministic summary. The user may explicitly request an AI draft and regenerate the reports to include it; all artifacts remain tied to the same dataset and filters. A changed dataset or filter invalidates the prior summary for the current view.

## 4. Data needs and future contract ownership

The required domains are production planning, production actuals, quality, and inventory. Users need traceable, validated records that support comparisons and explain data coverage. This PRD does not define a final schema.

`docs/data/DATA_CONTRACT.md` is a **missing future source of truth**, not an existing dependency that can be assumed satisfied. Before data behavior is implemented, document and resolve field names, types, units, row grain, keys, joins, domain completeness, permitted normalization, duplicate handling, missing values, and import limits there. Do not infer those rules from an LLM.

The earlier PRD's field table and exact file constraints are removed here to avoid maintaining a competing schema. D01–D05/D10 retain high-level proposals for review: fixed templates, complete batches, one product per line-shift, snapshot inventory, and whole-batch replacement. They are not finalized rules. Source traceability and visible errors are required; the exact metadata representation and persistence mechanism belong to later design.

## 5. Analytics needs and future business-rule ownership

Numerical KPIs and rule-based anomalies must be deterministic, consistent across views and reports, and traceable to validated inputs. Invalid or unavailable data must not silently become trustworthy-looking results. LLM wording is not a business-rule source.

`docs/data/KPI_DEFINITIONS.md` is a **missing future source of truth** for formulas and metric semantics. The existing charter section 6 contains preliminary KPI examples; consult that source rather than duplicating its formulas here. Those examples are not finalized for the expanded four-domain product. Resolve metric scope, numerator/denominator meaning, aggregation, zero/missing-value behavior, units, rounding, and applicable filters before implementation.

| Reference ID | Candidate analytics need | Status / source |
| --- | --- | --- |
| K01 | Total output | Charter example; formal definition pending |
| K02 | Good output | Charter example; formal definition pending |
| K03 | Production attainment | Charter example; formal definition pending |
| K04 | Reject rate | Charter example; formal definition pending |
| K05 | Unplanned downtime rate | Charter example; formal definition pending |
| K06 | Per-item stock | Proposed inventory indicator; D04 unresolved |
| K07 | Low-stock item count | Proposed inventory indicator; D04 unresolved |

K01–K07 are traceability labels, not an approved count or formula specification. Snapshot selection, carry-forward, minimum-stock meaning, compatible units, and inventory filter behavior must be resolved in the Data Contract/KPI Definitions, with UI behavior referenced from the future UI Spec.

| Rule reference | Candidate observation | Decision status |
| --- | --- | --- |
| R01 | Low production attainment | Threshold, comparator, grain, and skipped cases pending D06 |
| R02 | High rejection level | Threshold, comparator, grain, and skipped cases pending D06 |
| R03 | High downtime | Threshold, comparator, grain, and skipped cases pending D06 |
| R04 | Low stock | Minimum-stock meaning and snapshot semantics pending D04/D06 |

The previous numerical thresholds were illustrative suggestions, not approved standards; they are withdrawn from this PRD as acceptance baselines. No numerical threshold is approved here. Document approved rule semantics once in a dedicated business-rule source before implementation; proposed location is a rule section in KPI_DEFINITIONS (ownership to resolve under D06). Link to that source from this PRD and tests.

Each eventual anomaly must expose its rule, observed value, comparison basis, affected data, and source evidence. Separate operational anomalies from validation failures. Counting, boundaries, multiple-rule matches, and skipped evaluations require explicit definitions; do not silently invent them. No causal diagnosis is required.

## 6. Feature requirements

Feature IDs map directly to user stories. Acceptance clauses AC1, AC2, etc. are referenced as `F01-AC1` throughout the companion document.

**Draft-detail rule:** The following inputs, behavior, edge cases, and acceptance clauses describe proposed behavior, not finalized business or technical specifications. A MUST feature is requested; its assumptions are not automatically approved. Numeric tolerances, filters, batching, layouts, and snapshot behavior below are conditional on the owning documents and decisions listed here. Do not use them to bypass missing definitions. Once decisions are approved, replace detailed business wording with references to the owning source rather than duplicating it.

| Features | Decisions / missing owning documents that gate detailed implementation |
| --- | --- |
| F01–F03, S01 | D01–D03/D10; DATA_CONTRACT |
| F04 | D05; DATA_CONTRACT and ARCHITECTURE |
| F05–F06 | D04/D06; DATA_CONTRACT and KPI_DEFINITIONS |
| F07–F10, S02 | D04/D08; KPI_DEFINITIONS and UI_SPEC |
| F11–F12 | D08/D09/D15; UI_SPEC and ACCEPTANCE_CRITERIA |
| F13 | D07; optional delivery commitment and AI evaluation criteria |
| C01 | Explicit scope approval; KPI_DEFINITIONS and ACCEPTANCE_CRITERIA |


### F01 — Upload Excel/CSV [MUST]

- **Business purpose:** Replace manual file consolidation with a defined intake.
- **User story:** As an analyst, I want to submit one complete batch so that all domains are analyzed together.
- **Input:** Files conforming to section 4.
- **Behavior:** Select files and domain assignments; show names, sizes, and detected domains; enforce supported formats and limits without activating data.
- **Expected output:** A staged batch or actionable upload failure.
- **Edge cases:** Missing/duplicate domains, corrupt or password-protected workbook, bad encoding, empty file, excess size/rows, mixed formats, formula cells.
- **Acceptance:** AC1: Equivalent Excel and CSV fixtures stage the same domain records. AC2: Every unsupported/incomplete case fails with its reason and preserves the active dataset. AC3: Upload alone does not change analytics.

### F02 — Validate schema and data [MUST]

- **Business purpose:** Prevent incorrect source data from becoming apparently trustworthy analytics.
- **User story:** As an analyst, I want precise diagnostics so that I can correct the source files.
- **Input:** Staged batch and documented schema/relationship rules.
- **Behavior:** Check schema, missing/invalid values, unique keys, ranges, cross-domain coverage and product agreement; collect actionable diagnostics rather than silently dropping rows.
- **Expected output:** Pass/fail status, affected locations, rule IDs, reasons, and counts.
- **Edge cases:** Blank versus zero, duplicate identical rows, reject count above output, nonfinite values, unmatched keys, unsupported extra fields.
- **Acceptance:** AC1: Seeded fixtures for every rule produce the expected failures and valid fixtures pass. AC2: Blocking failures prevent persistence of the batch and new KPI/report generation. AC3: Diagnostics identify source row/field when available and file/domain for structural errors.

### F03 — Normalize and transform [MUST]

- **Business purpose:** Make permitted formatting differences consistent without altering operational meaning.
- **User story:** As an analyst, I want transparent normalization so that reported data remains explainable.
- **Input:** Staged values eligible for documented conversions.
- **Behavior:** Trim text, canonicalize permitted dates and numeric representations, preserve IDs, join production domains one-to-one, and revalidate transformed values. Format validation recognizes only these permitted conversions.
- **Expected output:** Canonical domain records and normalization log with original and normalized values.
- **Edge cases:** Leading-zero IDs, ambiguous dates, fractional counts, locale-specific decimal strings, duplicate keys created by trimming.
- **Acceptance:** AC1: Equivalent permitted representations normalize identically. AC2: Ambiguous or meaning-changing conversions fail rather than guess. AC3: Post-normalization collisions block import and source references survive transformations.

### F04 — Persist normalized data [MUST]

- **Business purpose:** Preserve a validated dataset between sessions and prevent partial updates.
- **User story:** As an analyst, I want accepted data to survive restart so that re-upload is unnecessary.
- **Input:** Fully validated normalized batch and provenance metadata.
- **Behavior:** Commit all four domains atomically; switch active snapshot only on success; treat equivalent re-imports as no-ops. Preserve previous active results on write failure.
- **Expected output:** Durable active dataset, batch identity, and import result.
- **Edge cases:** Interrupted write, unavailable storage, repeated batch, revised complete batch, restart without prior data.
- **Acceptance:** AC1: Restart reproduces accepted records and metadata. AC2: Simulated commit failure leaves the former dataset intact with no partially active domains. AC3: Equivalent re-import does not increase record counts; revised batch replaces rather than appends.

### F05 — Calculate KPIs [MUST]

- **Business purpose:** Provide consistent, auditable manufacturing indicators.
- **User story:** As a manager, I want defined KPIs so that I can compare operations reliably.
- **Input:** Active normalized dataset and applicable filters.
- **Behavior:** Calculate the approved metrics referenced by K01–K07 after the future KPI_DEFINITIONS is established; return coverage and numerator/denominator evidence for ratios.
- **Expected output:** Reusable metric results shared by all views and exports.
- **Edge cases:** Zero denominators, empty selection, weighted aggregation, over-target output, stale/missing inventory snapshots.
- **Acceptance:** AC1: Independent fixtures match exact counts and percentages within 0.01 percentage points. AC2: Zero denominators and empty selections show N/A appropriately. AC3: Inventory uses one eligible snapshot per item and never adds daily balances or incompatible units.

### F06 — Detect rule-based anomalies [MUST]

- **Business purpose:** Direct attention to specific deviations needing investigation.
- **User story:** As a supervisor, I want evidence-backed exceptions so that I know which records to inspect.
- **Input:** Valid selected records, calculated values, and approved, versioned rules corresponding to candidate R01–R04; numerical thresholds are not yet defined.
- **Behavior:** Apply fixed comparisons at the defined grain and retain evidence; separate skipped checks from passing checks.
- **Expected output:** Filtered anomaly list, rule-record count, and skipped-evaluation count.
- **Edge cases:** Exact boundary, multiple rules on one row, undefined ratio, carried-forward stock, no anomalies.
- **Acceptance:** AC1: Below/equal/above-boundary fixtures produce exact expected results for all rules. AC2: Every result has rule and source evidence. AC3: Repeated input/settings produce identical results; N/A does not become a normal result.

### F07 — Overview [MUST]

- **Business purpose:** Give managers a concise view of the factory dataset.
- **User story:** As a manager, I want an overview so that I can locate areas needing attention.
- **Input:** Shared KPI/anomaly results, validation status, batch metadata, date/line/shift filters.
- **Behavior:** Show K01–K05 and K07, a daily output trend, anomaly counts, data coverage, and links/navigation to the other four areas. Label inventory as date-based and independent of line/shift filters.
- **Expected output:** One summary area within the application.
- **Edge cases:** No active data, empty filtered results, failed latest import with older active data, no eligible inventory snapshot.
- **Acceptance:** AC1: Cards and trend reconcile with F05 for selected records. AC2: Visible filters/batch identity prevent confusion about the analyzed data. AC3: No-data states and inventory scope are explicit.

### F08 — Production [MUST]

- **Business purpose:** Explain plan-versus-actual production and downtime differences.
- **User story:** As a production supervisor, I want trends and line comparisons so that I can find missed targets.
- **Input:** Joined production records and shared date/line/shift filters.
- **Behavior:** Show planned versus actual output, K01–K03 and K05, daily trend, line comparison, and associated R01/R03 record details.
- **Expected output:** Production analysis with supporting rows/source references.
- **Edge cases:** Zero plan, zero output, attainment over 100%, one line, no selected records.
- **Acceptance:** AC1: Chart totals and detail rows reconcile with selected KPIs. AC2: Over-100% attainment remains visible without truncation. AC3: Undefined ratios and empty results are labeled, not silently replaced with zero.

### F09 — Quality [MUST]

- **Business purpose:** Expose rejection patterns without implying causes.
- **User story:** As quality staff, I want reject trends and source evidence so that I can investigate affected shifts.
- **Input:** Joined quality/actuals records and shared filters.
- **Behavior:** Show produced, rejected and good quantities, K04 daily trend and line comparison, and R02 details.
- **Expected output:** Quality analysis and traceable affected records.
- **Edge cases:** Zero output, no rejects, differing daily volumes, missing quality source records rejected at import.
- **Acceptance:** AC1: Quality totals agree with Production and K02/K04. AC2: Aggregate reject rate uses summed quantities. AC3: Zero output is N/A for rate; no-reject positive output is 0%.

### F10 — Inventory [MUST]

- **Business purpose:** Identify items below minimum using transparent snapshot coverage.
- **User story:** As inventory staff, I want as-of quantities so that I can review low-stock items.
- **Input:** Inventory snapshots, shared date range, optional local item selection.
- **Behavior:** Show K06 with units, minimum, snapshot date, carried-forward status, K07, and R04; line/shift filters have no effect. Item selection affects only this area and is not silently applied to full reports.
- **Expected output:** Per-item inventory table and below-minimum count with coverage.
- **Edge cases:** Missing prior snapshot, old snapshot, unit mismatch blocked at intake, stock equal to minimum, multiple snapshots across dates.
- **Acceptance:** AC1: Choose latest snapshot at or before end date, never a future snapshot. AC2: Carry-forward and missing coverage are visible; equality is not low stock. AC3: Changing line/shift does not change inventory; scope and item filtering are labeled.

### F11 — Reports & Insights / Excel export [MUST]

- **Business purpose:** Produce reusable management tables without manual spreadsheet assembly.
- **User story:** As an analyst, I want an Excel report so that managers can inspect results outside the application.
- **Input:** Current batch, shared filters, KPI/anomaly evidence, metadata, and current summary.
- **Behavior:** In Reports & Insights, preview report scope and generate a fixed `.xlsx` report with Overview, Production, Quality, Inventory, Anomalies, Data Quality, and Summary sheets. Inventory includes all items as of the end date, independent of line/shift and Inventory's local item filter. Export values as report data, never executable source formulas.
- **Expected output:** Downloadable Excel report with consistent units, dates, definitions, provenance, and summary type.
- **Edge cases:** No active data, empty production selection with inventory coverage, file write failure, strings resembling formulas, outdated summary.
- **Acceptance:** AC1: Exported values reconcile exactly with shared results at displayed precision. AC2: Workbook opens without repair; untrusted text is not executed as a formula. AC3: Missing dataset blocks export; otherwise empty domains are labeled; export failure is visible and retryable. AC4: Changed scope cannot export a stale summary.

### F12 — PDF report [MUST]

- **Business purpose:** Provide a readable management artifact suitable for sharing.
- **User story:** As a manager, I want a PDF report so that I can review a stable presentation of the results.
- **Input:** The same report scope and results as F11.
- **Behavior:** Generate one fixed-layout PDF containing scope/coverage, KPI definitions and values, production/quality trends, inventory summary, anomaly summary, and management summary. Include the first 20 anomaly details in stable date/rule/key order and label any truncation; the Excel report contains the full list.
- **Expected output:** Downloadable PDF with readable tables/charts, page numbers, batch identity, and creation time.
- **Edge cases:** Long IDs, many anomalies, no anomalies, unavailable values, export failure, multi-page tables.
- **Acceptance:** AC1: PDF and Excel agree on facts and filters. AC2: Visual review of representative long/empty/full fixtures finds no clipped text, overlap, or unreadable charts. AC3: Truncation is disclosed and failures leave application data unchanged.

### F13 — Optional AI management summary [COULD proposed; release priority pending D07]

- **Business purpose:** Demonstrate faster narrative preparation grounded in validated results.
- **User story:** As a manager, I want an optional AI draft so that I can review and adapt a concise management summary.
- **Input:** Explicit generation request plus a bounded aggregate fact set from current report scope, rule evidence, and limitations; one optional model provider.
- **Behavior:** Generate observations, limitations, and investigation questions. Label AI authorship and human-review requirement. Do not calculate KPIs, infer causes as facts, or send raw rows. Always offer a deterministic template summary; use it for missing credentials, timeout, failure, or an unusable response. Tie the draft to batch/filter/rule version and invalidate it on changes.
- **Expected output:** Labeled draft or labeled fallback, optionally included in regenerated Excel/PDF reports.
- **Edge cases:** No data, no anomalies, N/A, unavailable provider, unsupported numerical claim, changed filters.
- **Acceptance:** AC1: Core workflow completes offline. AC2: In at least five fixed evaluation scenarios every numeric claim matches supplied facts and unavailable measures remain unavailable; unsupported explanations are not stated as facts. AC3: Simulated API failures return fallback without losing reports/data. AC4: Changing scope invalidates the draft; generation requires explicit user action.

## 7. Nonmandatory feature specifications

### S01 — Downloadable input guidance [SHOULD]

- **Business purpose / user story:** As an analyst, I want examples so that I can prepare valid inputs with less trial and error.
- **Input:** Versioned schemas and clean/invalid synthetic examples.
- **Behavior / output:** Expose the four-domain Excel template, equivalent CSV examples, and field/rule dictionary for download.
- **Edge cases:** Outdated schema example, absent sample asset.
- **Acceptance:** AC1: Clean examples pass F02; deliberately invalid examples produce documented errors. AC2: Assets identify their schema version and synthetic origin.

### S02 — Basic accessibility [SHOULD]

- **Business purpose / user story:** As a user, I want readable, keyboard-operable controls so that I can navigate the analysis reliably.
- **Input:** Five areas, controls, charts, and validation messages.
- **Behavior / output:** Provide labeled controls, visible keyboard focus, textual status labels, and table equivalents for charts.
- **Edge cases:** Color-only anomaly indication, long diagnostic text, empty chart.
- **Acceptance:** AC1: Upload, filtering, navigation, and export can be operated by keyboard. AC2: Status meaning is available without color and each chart's values can be inspected as text/table.

### C01 — Prior-period comparison [COULD]

- **Business purpose / user story:** As a manager, I want a previous-period comparison so that I can put current production performance in context.
- **Input:** Current date range and immediately preceding equal-length range in the active dataset, with identical line/shift filters.
- **Behavior / output:** Compare K01–K05; show absolute changes and percentage-point changes for rates. Do not add inventory comparisons.
- **Edge cases:** Missing days, empty previous period, undefined rate.
- **Acceptance:** AC1: Independently calculated comparison fixtures reconcile. AC2: Missing coverage is shown and invalid comparisons display N/A, with no implied improvement.

## 8. Cross-cutting acceptance and delivery evidence

These are draft validation needs. Final release gates belong in the missing future `docs/quality/ACCEPTANCE_CRITERIA.md`; procedures belong in `docs/quality/TEST_PLAN.md`. Numeric checks and conditional behavior require approved business definitions. V0 documentation completion does not claim product acceptance.

- MUST: A clean four-domain Excel batch and equivalent CSV batch complete the entire offline workflow and reconcile. Invalid batches never become active.
- **Proposed performance evaluation, not a release gate:** The charter has an end-to-end timing target; the previous PRD split it into separate processing/export targets without approval. Resolve workload, hardware, timing boundary, and limits under D14 in future TEST_PLAN/ACCEPTANCE_CRITERIA. Do not present either interpretation as validated performance for the expanded scope.
- MUST: Test calculations independently, all validation rules, atomic failure/restart, re-import, anomaly boundaries, filter consistency, and both export formats. Record actual results; do not claim success based on requirements alone.
- MUST: Preserve source traceability and deterministic non-AI results across repeat runs, excluding timestamps. Keep credentials outside source and export artifacts. Use synthetic data for demonstration.
- MUST: Document local setup, schemas, KPI/rule definitions, replacement behavior, limitations, and a three-to-five-minute walkthrough. Demonstrate at least one invalid-input case and offline fallback.
- SHOULD: Measure hands-on time against the same documented manual report task; retain the charter's 50% reduction target as an unverified portfolio outcome, not a guaranteed customer benefit.
- Document deliverables in English and Simplified Chinese with matching IDs and acceptance criteria. Bilingual application UI and bilingual report generation are not implied by this documentation requirement.

## 9. Ambiguities and proposed decisions

D01–D11 and D14–D15 remain open proposals; D12 records the explicit bilingual-documentation instruction and D13 records the completed V0 creation. No open item authorizes implementation. Record approval and the owning document when resolved.

| ID | Ambiguity | Proposed decision and consequence |
| --- | --- | --- |
| D01 | Four domains in one file or separate uploads? | Accept one four-sheet Excel workbook or four assigned CSV files per batch. No partial-domain imports. |
| D02 | Product, shift, and time granularity? | One product per date/line/shift; one site, one local calendar, no time-of-day or timezone conversions. Mixed-product shifts need a later contract revision. |
| D03 | Can plan/actual/quality coverage differ? | Require identical keys and explicit zero records. This avoids incomplete-rate bias but requires source preparation. |
| D04 | What does inventory mean? | As-of stock snapshots with supplied minimum levels, no movements, valuation, or production reconciliation. Carry-forward dates are visible. |
| D05 | Incremental import, corrections, history? | Whole-batch active snapshot replacement, equivalent re-import no-op, atomic persistence across restart. No merge/history UI. Storage choice deferred to design. |
| D06 | Which anomalies and thresholds? | Consider simple R01–R04 observations, but choose no numeric defaults until explicitly documented. Propose KPI_DEFINITIONS as the rule-semantics owner; confirm ownership, thresholds, comparators, grain, and skipped/counting behavior. No rule editor. |
| D07 | What is the optional AI release commitment? | Latest instructions say AI is optional; retract the earlier unapproved MUST-capability interpretation. Keep F13 as COULD proposed until release priority is agreed. Core analytics/reports never require AI; a deterministic summary is proposed independently of provider delivery. |
| D08 | How do filters affect inventory and reports? | Shared date/line/shift for production/quality; inventory as of end date ignores line/shift. Inventory-only item filter does not affect full reports; scope preview states this. |
| D09 | Must original HTML export remain? | Replace it with PDF, keeping two formats. Retaining HTML would be an additional scope decision. |
| D10 | Input limits and locale handling? | 10 MB / 10,000 total rows; strict ISO/Excel dates, UTF-8 CSV, fixed schema, discrete production units. No automatic locale or unit inference. |
| D11 | Effort and breadth after expansion? | Re-estimate the expanded MUST baseline. Cut COULD and defer SHOULD features before adding complexity; do not assume the old estimate still applies. |
| D12 | Meaning of bilingual output? | User explicitly requested paired English/Chinese documents; recorded as a documentation requirement. Application/report language remains a separate decision. |
| D13 | Repository agent guidance | AGENTS.md V0 and its Chinese counterpart now exist; the prior missing-file note is obsolete. V1 review remains required before implementation. |
| D14 | Performance acceptance boundary? | Reconcile charter end-to-end timing versus previous PRD split targets; record agreed workload, hardware, and measurement procedure in quality documents. |
| D15 | Report detail and layout limits? | Seven Excel sheets and a 20-row PDF anomaly preview are previous draft suggestions, not approved limits. Resolve layout, truncation, and scope disclosure in UI_SPEC/ACCEPTANCE_CRITERIA. |

## 10. Scope review

Keep the requested domains and areas; snapshot-only analytics is a proposal requiring D04 resolution, not an implementation instruction. Remove inventory transaction entry, multi-product time allocation, arbitrary file mapping, incremental reconciliation, dynamic dashboards, anomaly configuration, and extra report formats from consideration. Five areas are navigation over shared data, not five independent applications. Reliable persistence is requested; atomic snapshot replacement is the D05 proposal, not a storage architecture decision. Distributed infrastructure remains excluded by AGENTS V0.

The largest remaining uncertainties are domain completeness, inventory semantics, and the expanded effort estimate. Resolve the relevant open decisions, reconcile the charter, establish the missing authoritative documents, and review AGENTS V1 before implementation. This document proposes the bounded behavior; it does not authorize or contain implementation.
