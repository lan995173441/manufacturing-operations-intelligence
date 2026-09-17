# Manufacturing Operations Intelligence — User Stories

Date: 2026-09-15  
Status: V0-aligned requirements draft, no implementation  
Requirement authority: PRD.md; Chinese counterpart: USER_STORIES.zh-CN.md

## 1. Reading this backlog

Stories use the same feature IDs as the PRD. Each acceptance reference points to its numbered clause there; the scenarios below provide observable examples, not replacement specifications. Inputs, behavior, outputs, edge cases, and business purpose are defined per feature in PRD sections 6–7. Consult the revised PRD decision register D01–D15 and AGENTS.md V0. Detailed scenarios are provisional where they depend on unresolved decisions or missing Data Contract/KPI Definitions. MUST identifies requested core capabilities, not approval of draft rules; SHOULD and COULD are unapproved proposals unless explicitly accepted; OUT OF SCOPE is excluded.

The analyst operates the local application; other personas describe the consumers of its views, not distinct accounts or permissions. Build one shared workflow, not separate systems for each persona. All fixture values below are synthetic illustrations, not authoritative business definitions or approved acceptance fixtures. Formalize rules in their owning documents before implementing tests against these examples.

## 2. Core MUST stories and optional AI proposal

### US-F01 — Submit a complete batch

**Story:** As a manufacturing analyst, I want to upload Excel or CSV data for planning, actuals, quality, and inventory so that I can analyze one coherent dataset.

**Priority:** MUST. **Depends on:** D01/D10 agreement. **Acceptance:** F01-AC1–AC3.

- Given equivalent four-sheet Excel and four-file CSV fixtures, when each is staged, then the same domain records are available for validation.
- Given a missing quality file, unsupported format, or oversized batch, when uploaded, then the reason is shown and the current dataset is unchanged.
- Given a valid staged batch, when no acceptance has occurred, then existing analytics still identify the previous batch.

### US-F02 — Locate invalid data

**Story:** As an analyst, I want schema and value errors tied to source locations so that I can correct the original spreadsheet without guessing.

**Priority:** MUST. **Depends on:** F01. **Acceptance:** F02-AC1–AC3.

- Given a missing required column, blank key, duplicate row, negative count, or mismatched domain key, when validated, then the relevant diagnostic is produced and the entire batch is blocked.
- Given 100 produced units and 101 rejected units, then the quality row and violated relationship are identified.
- Given explicit valid zero values, then they are not reported as missing. Valid fixtures pass all rules.

### US-F03 — Normalize without hidden corrections

**Story:** As an analyst, I want permitted formatting differences standardized transparently so that the normalized records retain their original meaning.

**Priority:** MUST. **Depends on:** F01/F02. **Acceptance:** F03-AC1–AC3.

- Given an ID ` 0012 `, when normalized, then it becomes `0012`, keeps its leading zeroes, and records the transformation and source.
- Given ambiguous date text or fractional produced counts, then the batch fails rather than guessing or rounding.
- Given keys that become duplicates after trimming, then post-normalization validation blocks the batch before persistence.

### US-F04 — Keep the accepted dataset

**Story:** As an analyst, I want accepted records retained across restart so that I can resume analysis without rebuilding my dataset.

**Priority:** MUST. **Depends on:** F02/F03; D05. **Acceptance:** F04-AC1–AC3.

- Given a successful import, when the application restarts, then all four domains and provenance metadata remain available.
- Given an existing active batch and a simulated write failure on a new batch, then the old batch stays intact and no new domain is partially active.
- Given an equivalent re-import, then counts do not grow; given a different valid full batch, then its snapshot replaces the active dataset rather than appending.

### US-F05 — Trust the indicators

**Story:** As an operations manager, I want consistent KPI definitions so that dashboard and report numbers support the same conclusion.

**Priority:** MUST. **Depends on:** F04. **Acceptance:** F05-AC1–AC3.

- Given two selected production records with planned units 100/300, produced units 80/300, rejects 4/6, planned minutes 100/300, and downtime 10/20, then K01 = 380, K02 = 370, K03 = 95.00%, K04 = 2.63%, and K05 = 7.50%.
- Given zero denominators or an empty selection, then ratios show N/A; a positive-output row with zero rejects shows a 0% reject rate.
- Given two stock snapshots of 12 and 7 for one item on successive dates, then the later eligible as-of balance is 7, not 19; distinct item units are never combined.

### US-F06 — Review explainable anomalies

**Story:** As a supervisor, I want fixed-rule exceptions with source evidence so that I can investigate specific operational deviations.

**Priority:** MUST. **Depends on:** F05; D06. **Acceptance:** F06-AC1–AC3.

- Given a valid record meeting the future approved trigger conditions for R01, R02, and R03, then results follow the approved counting convention. Thresholds and counting remain unresolved under D06.
- Given values below, equal to, and above an approved threshold, then each outcome matches its documented comparator. The earlier numerical thresholds and assumed equality behavior are not approved defaults.
- Given an undefined ratio, then its rule is reported as not evaluated; every triggered result includes threshold, observed value, key, and source reference.

### US-F07 — Understand the overview

**Story:** As an operations manager, I want a concise Overview so that I can decide which operational area to inspect next.

**Priority:** MUST. **Depends on:** F05/F06. **Acceptance:** F07-AC1–AC3.

- Given active data, when date/line/shift filters change, then production cards and daily output trend reconcile with the selected records.
- Given inventory results alongside production cards, then their independent date-based scope is explicit.
- Given a rejected latest import with an older active batch, then the old batch identity and latest failure are visible rather than implying the failed file was analyzed.

### US-F08 — Compare plan and actual production

**Story:** As a production supervisor, I want planned-versus-actual output and downtime views so that I can locate missed targets by period, line, and shift.

**Priority:** MUST. **Depends on:** F05/F06/F07. **Acceptance:** F08-AC1–AC3.

- Given a selected period, then plan/actual charts, line totals, detail rows, and KPIs reconcile.
- Given 120 units against a 100-unit plan, then 120% attainment is visible without being capped at 100%.
- Given no selected production records, then the area displays an explicit empty state rather than fabricated zero performance.

### US-F09 — Investigate quality results

**Story:** As quality staff, I want rejection trends and affected records so that I can investigate poor-quality shifts without assuming their cause.

**Priority:** MUST. **Depends on:** F05/F06/F07. **Acceptance:** F09-AC1–AC3.

- Given the US-F05 fixture, then Quality shows 380 produced, 10 rejected, 370 good, and 2.63% rejected, matching Production and shared metrics.
- Given records of different volumes, then the rate is a ratio of summed counts, not an average of row percentages.
- Given no output, then the rate is N/A; given positive output with no rejects, then it is 0%.

### US-F10 — Review inventory as of a date

**Story:** As inventory staff, I want per-item balances and minimum comparisons with snapshot dates so that I can identify low stock and understand data freshness.

**Priority:** MUST. **Depends on:** F05/F06/F07; D04/D08. **Acceptance:** F10-AC1–AC3.

- Given snapshots on September 1 and September 10 and an end date of September 5, then the September 1 snapshot is selected; if the range begins September 3, it is labeled carried forward.
- Given an item whose first snapshot is September 10, then it is N/A as of September 5 and counted as missing coverage, not zero stock.
- Given stock 5 and minimum 5, then no low-stock result appears. Changing line/shift has no effect; the local item filter is clearly scoped to Inventory.

### US-F11 — Export an Excel management report

**Story:** As an analyst, I want a fixed Excel report so that managers can inspect and reuse validated analytics without manual report assembly.

**Priority:** MUST. **Depends on:** F05–F10 and the approved non-AI report scope. F13 is not a core export prerequisite. **Acceptance:** F11-AC1–AC4.

- Given a report scope preview, when export runs, then the workbook includes all seven specified sheets and values match shared results at displayed precision.
- Given a local Inventory item filter, then the report preview states that the full report contains all inventory items; line/shift still apply only to production/quality.
- Given source text resembling a spreadsheet formula, then it remains non-executable text in the report.
- Given no active dataset or a write failure, then the application shows an appropriate failure; given changed filters, then no previous-scope summary is exported.

### US-F12 — Export a readable PDF

**Story:** As a manager, I want a PDF management report so that I can share a stable, readable presentation of the analysis.

**Priority:** MUST. **Depends on:** F11 shared report scope/results. **Acceptance:** F12-AC1–AC3.

- Given the same dataset and filters, then PDF and Excel state matching facts, definitions, and scope.
- Given long IDs or multi-page content, then visual inspection finds no clipped text, overlap, or unreadable charts.
- Given 25 anomalies, then the PDF includes the first 20 in the specified stable order, discloses omitted details, and states that Excel has the complete list. Export failure does not change data.

### US-F13 — Request an optional grounded summary

**Story:** As a manager, I want an optional AI-assisted draft so that I can review a concise explanation of calculated results and investigation questions.

**Priority:** COULD proposed; optional AI release commitment pending D07. **Depends on:** F05/F06 and shared report scope; D07. **Acceptance:** F13-AC1–AC4.

- Given no model credentials or a simulated timeout, then the deterministic labeled summary is available and the offline reporting workflow completes.
- Given an explicit request, then the model receives bounded aggregate facts only; the draft is labeled AI-assisted and requiring human review.
- Given at least five fixed scenarios covering normal results, anomalies, N/A, no anomalies, and provider failure, then factual evaluation and fallback meet F13 acceptance.
- Given changed filters or a new batch, then the previous draft is invalidated; a current-scope summary must be used before export. No automatic operational action follows the draft.

## 3. SHOULD and COULD stories

### US-S01 — Obtain input guidance [SHOULD]

As an analyst, I want downloadable examples and a dictionary so that I can prepare files correctly. **Depends on:** agreed input contract. **Acceptance:** S01-AC1–AC2. Clean Excel/CSV examples pass validation; deliberately invalid examples produce documented errors; all examples show schema version and synthetic origin. Missing/outdated assets must not be presented as valid current templates.

### US-S02 — Navigate accessibly [SHOULD]

As a user, I want labeled controls, keyboard navigation, and textual chart values so that I can inspect results without relying on a mouse or color alone. **Depends on:** F01/F07–F12. **Acceptance:** S02-AC1–AC2. Keyboard operation reaches upload, filters, all five areas, and export; statuses are understandable without color and charts have readable data equivalents.

### US-C01 — Compare the previous period [COULD]

As a manager, I want an immediately preceding equal-length period comparison so that I can contextualize current production results. **Depends on:** F05 and completed MUST acceptance. **Acceptance:** C01-AC1–AC2. K01–K05 comparisons match independent fixtures under identical line/shift filters; missing coverage and unavailable comparisons are explicit. Rates use percentage-point changes; inventory comparison remains excluded.

## 4. OUT OF SCOPE requests

Do not create implementation stories for machine integration/control, work orders, inventory transactions or valuation, arbitrary spreadsheet mapping, incremental domain updates, rule editors, prediction/ML models, chatbots, multiple accounts, scheduling/email, extra report formats, or cloud infrastructure. A user persona does not imply a new role/account system. Bilingual documentation does not imply bilingual application functionality.

## 5. Traceability and release boundary

| Workflow / application area | Stories | Priority |
| --- | --- | --- |
| Upload → validate → normalize → persist | US-F01–US-F04 | MUST |
| KPIs → rule anomalies | US-F05–US-F06 | MUST |
| Overview | US-F07 | MUST |
| Production | US-F08 | MUST |
| Quality | US-F09 | MUST |
| Inventory | US-F10 | MUST |
| Reports & Insights, Excel/PDF | US-F11–US-F12 | MUST |
| Optional summary | US-F13 | COULD proposed; D07 open |
| Input guidance / accessibility | US-S01–US-S02 | SHOULD |
| Prior-period comparison | US-C01 | COULD |

Final release acceptance will be established in the future Acceptance Criteria document after relevant decisions are resolved. The core F01–F12 workflow must not depend on optional F13 or an API key. Feature dependencies are logical contracts, not implementation sequencing instructions. The proposed non-AI summary belongs to core report behavior if approved; no provider integration is required for it.

Before implementation, resolve the PRD decision register, especially batch structure, production completeness, inventory semantics, replacement policy, and re-estimated effort. Record accepted decisions in both language versions. AGENTS.md V0 now exists; read it and review the V1 transition before implementation. No story is marked implemented or accepted by this document.
