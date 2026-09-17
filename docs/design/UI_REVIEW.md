# Streamlit UI review

Date: 2026-09-16. Scope: current portfolio MVP, five application areas. Chinese counterpart: [UI_REVIEW.zh-CN.md](UI_REVIEW.zh-CN.md).

## Basis and limits

Reviewed AGENTS.md, ARCHITECTURE.md, PRD.md, the UI and service result contracts. UI_SPEC.md does not exist. The historical V0 inventories and draft requirements are not evidence of finalized design approval. Current functionality and the explicit UI-review task define this change's boundary.

Evidence comes from UI code inspection and Streamlit AppTest runs against synthetic data, including all five areas and failure states. The local server responds with HTTP 200. Playwright could not launch Chrome because the system sandbox rejected its process communication port; no new screenshot or pixel-level review was completed. Density, wrapping and layout recommendations below derive from declared component order and chart sizes and need browser verification. This is an engineering/design assessment, not a user research study.

Existing strengths: service-owned calculations, six Overview metrics, consistent Plotly colors, suitable planned/actual time series and line comparisons, explicit empty states, and explanatory inventory scope text. The largest immediate risks are misleading check status and unclear data activation/validation feedback.

Priority: **P0** can mislead an operational conclusion, unexpectedly replace the working dataset, or obscure import correctness. **P1** materially improves routine comprehension and task efficiency. **P2** improves presentation or expectation-setting after the critical work. Exactly ten improvements are ranked below; only the three P0 items are implemented.

## Ranked improvements

| Rank / ID | Priority | Finding and consequence | Recommended change | Status |
| --- | --- | --- | --- | --- |
| 1 / UX-01 | P0 | Alert rendering previously showed green “No rules triggered” for zero checks, missing coverage or unsupported schema. A missing threshold appeared as a low-emphasis information message, even though all anomaly checks were disabled by the existing service. | Distinguish not configured, failed, no data, incomplete and completed checks. Only show a positive no-alert result when status is valid, at least one check completed, and none were skipped. Show completed/skipped counts and skipped reasons. Provide an actionable threshold input error without internal type names. | Implemented. Detection results, configuration and thresholds unchanged. |
| 2 / UX-02 | P0 | “Load synthetic demo data” and upload activation could replace the active batch immediately without explaining replacement versus append. An operations manager could lose their current working view while exploring. | Explain that all four active datasets are replaced; require an acknowledgement before either activation when data exists. Keep first-run demo loading direct. Reset the acknowledgement after an attempt, including a rejected upload or unchanged re-import. | Implemented. Atomic persistence and no-op behavior unchanged. |
| 3 / UX-03 | P0 | Upload feedback omitted normalization evidence, unchecked-row counts, workbook sheet and related-record locations. Users could not audit converted values or locate cross-file failures fully; persistence errors exposed raw internal text. | Show validation counts, unchecked content, severity, rule, full source locations and correction guidance. Expose original/normalized values in a collapsed, paginated audit. Explain save failures and recovery plainly; accurately label unchanged re-imports. | Implemented. Validation and normalization rules unchanged. |
| 4 / UX-04 | P1 | Navigation follows setup, threshold, uploads and four filter controls. On smaller screens, switching between the five areas requires discovering controls far down the sidebar. | Put area navigation first, routine filters next and occasional data setup in a separate collapsible section. Keep navigation visible in the empty state. | Deferred. |
| 5 / UX-05 | P1 | Main-page scope text lists dates and batch, but omits selected line/product values. Inventory presents controls that do not apply to it; explanatory captions are separated from those controls. | Show a concise active scope summary. Label the inventory end-date meaning beside its filters and disable or clearly mark inapplicable controls while preserving production selections. | Deferred; preserve authoritative filtering semantics. |
| 6 / UX-06 | P1 | Labels such as “line-minutes per slot,” the long `12661.000 line-minutes` metric, and Completed Orders `N/A` require domain interpretation. The completion reason is technically correct but not plain management language. | Add short contextual metric help, clarify a slot as a production date/line/shift, distinguish unavailable from zero, and use presentation-only number/unit formatting. Explain that completion events are missing without inventing an order-count proxy. | Deferred; no formula or result changes. |
| 7 / UX-07 | P1 | Quality uses 90 pairs of good/scrap quantity bars. Because good output dominates, changes in scrap are difficult to compare and can be confused with volume changes. | Prefer a separate scrap-focused trend or approved service-supplied rate trend, retaining volumes as supporting context. Keep production time series and line comparisons. | Deferred. Any additional calculated series belongs in the service/domain and needs a separate task. |
| 8 / UX-08 | P1 | Alert previews show the first five detector entries, encoded entity keys and only the start date; thresholds and observed values are buried in explanations. The preview is not documented as a priority order. | Label the preview accurately and show existing structured observed value, threshold, unit and full date range with readable entity fields. Consider a severity view without altering anomaly membership or assigning new severity rules. | Deferred. |
| 9 / UX-09 | P2 | Reports & Insights reveals that downloads are unavailable only after the trend and alert table. A first-time visitor can spend time looking for a nonexistent export action. | Place an explicit preview-only availability notice near the heading; keep existing insight content. Do not add disabled decorative export buttons or implement reporting in this task. | Deferred. |
| 10 / UX-10 | P2 | Production stacks three full-width 330-pixel charts; Overview repeats a “Production trend” section heading and a chart title. Information takes more vertical space than its complexity requires. | Consider pairing the two line-comparison charts on wide screens, reduce redundant headings, and consistently separate primary KPIs, exceptions and supporting detail. Retain the restrained palette and test narrow layouts before changing chart sizes. | Deferred; browser-based layout validation required. |

## P0 acceptance and implementation boundary

- UX-01: no green all-clear for `no_data`, `invalid_data`, `unsupported_schema`, partial coverage, zero evaluated checks or skipped checks; valid complete non-triggering results remain positive. Configuration errors remain recoverable. Skipped reasons are visible without changing evaluation.
- UX-02: both activation buttons are disabled without acknowledgement when data is active; acknowledging one does not authorize the other. First-run demo loading works without acknowledgement. A rejected batch preserves the active identity and requires fresh acknowledgement for another attempt.
- UX-03: source diagnostics show sheet/row/field and related records; normalization pages expose all INFO entries, 100 at a time, with original and normalized values. Counts come from the validation result. Failed saves do not claim activation or show raw persistence diagnostics.
- Changed production code is confined to `ui/app.py`. No KPI, rule, schema, service, SQL, reporting implementation or dependency changes. Tests and bilingual review/execution-plan documentation accompany the UI changes.

## Verification

- `pytest tests/test_dashboard.py -q`: **12 passed in 13.53s**, including 10 new cases.
- `pytest -q`: **103 passed in 17.76s**.
- `ruff check .`: **All checks passed**. The two edited Python files were also formatted with Ruff.
- Separate AppTest walkthrough: all five areas render without exceptions. With the demo threshold explicitly set to 120, Overview/Reports show 52 alerts. Sample KPIs remain 98.01% attainment, 97.79% good yield and 2.21% scrap; Completed Orders remains N/A under the current schema.
- SHA-256 verification: every domain, service and data module is unchanged from the pre-edit baseline.
- Browser screenshot verification remains unavailable due to the sandbox restriction described above. No claim of completed pixel-level visual validation.
