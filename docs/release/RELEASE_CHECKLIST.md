# RC1 release checklist — Manufacturing Operations Intelligence

Date: 2026-09-17. Status: **candidate prepared; handover blocked**. Chinese counterpart: [RELEASE_CHECKLIST.zh-CN.md](RELEASE_CHECKLIST.zh-CN.md).

This is an evidence audit of the original [PRD](../product/PRD.md) draft and [Acceptance Criteria](../quality/ACCEPTANCE_CRITERIA.md). **PASS** means the stated observable behavior has test or inspection evidence, **FAIL** means an observed mismatch, and **NOT TESTED** means evidence is insufficient or a business decision is still required. A passing test of a provisional formula is not product-owner approval. Feature rows assess the feature's detailed behavior; their numbered acceptance clauses are assessed separately.

## Final v1.0.0 release disposition — 2026-09-20

**Decision:** Released as `v1.0.0` after explicit release-approver acceptance of the exceptions below. This decision does not rewrite the historical RC1 findings in this document or represent missing evidence as PASS.

| Final-gate item | Disposition | Evidence / limitation |
| --- | --- | --- |
| RC BLOCKER/HIGH engineering defects | Closed | `a641ac7` fixes RC identity and test-plan coverage; `3114b65` fixes the summary-report, filter, preview/evidence, and PDF-definition defects with regression tests. |
| Automated engineering validation | PASS | On the final-version metadata change, Ruff passed and all 140 tests passed in bounded groups. |
| UAT | Accepted exception | The release approver reports UAT complete, but no UAT plan, results, scenario evidence, or sign-off artifact is present in this repository; this audit cannot independently verify critical UAT cases. |
| Product-owner decisions BA-01–BA-08 | Accepted exception | No dated decision records are present. Candidate KPI/anomaly/data-contract semantics remain limited to the synthetic demonstration. |
| Performance target | Accepted exception | No approved workload, hardware boundary, or target is recorded. |
| Historical RC1 table below | Historical record | Its F01, F06–F12 dashboard/report failures predate `3114b65`; its remaining FAIL/NOT TESTED rows remain evidence gaps or draft-governance findings unless separately resolved. |

**Release scope:** local, single-user use with clearly labelled synthetic data only. Do not use this release for production control, compliance decisions, public hosting, or confidential customer data.

## Formal release candidate freeze — 2026-09-19

- **Release branch:** `release/v1.0.0`
- **Recommended candidate version:** `v1.0.0-rc.1`; no Git tag has been created.
- **Freeze status:** Active. New features, new KPIs, AI scope expansion, integrations, infrastructure changes, broad refactors, and dependency upgrades are prohibited. Only release-blocking/high-severity fixes, regressions, security or reliability fixes, necessary usability corrections, and release documentation/metadata may proceed.
- **Baseline validation:** `.venv/bin/ruff check .` passed; `.venv/bin/pytest -q` passed **138 tests in 34.23s**; documented `.venv/bin/pytest -v` passed **138 tests in 33.34s** on Python 3.12.2.
- **Pending:** UAT, product-owner decisions BA-01–BA-08, PRD/charter reconciliation, and final release approval. This freeze does not change the RC1 **NO GO for handover** decision below.

## RC1 validation record

| Check | Result | Evidence |
| --- | --- | --- |
| Full suite | PASS | Python 3.12.2, pytest 9.1.1: `.venv/bin/pytest -v` → **138 passed in 36.69s**. |
| Lint | PASS | `.venv/bin/ruff check .` → `All checks passed!` |
| App startup | PASS | `.venv/bin/streamlit run streamlit_app.py --server.address=127.0.0.1 --server.port=8766 --server.headless=true`; `lsof` showed only `TCP 127.0.0.1:8766 (LISTEN)`; `/_stcore/health` returned HTTP 200. Process stopped after check. |
| Synthetic demo | PASS | Fresh temporary SQLite: `load_sample_data()` accepted 5,220 rows: plan/actual/quality **540 each**, inventory **3,600**; generator scope **90 days, 3 lines, 20 products, 40 materials**. See `tests/data/test_synthetic.py`. |
| Excel/PDF | PASS | Same scope and analytics payload produced a **23,190-byte XLSX** with seven required sheets and a **31,737-byte PDF** with `%PDF` signature. `tests/test_reporting.py` checks section text, KPI equality, full anomaly list, long-scope pagination and independent renderer failure. This is structural/content validation; complete visual fixture review remains NOT TESTED below. |
| AI disabled | PASS | With `MOI_AI_ENABLED=false`, no key, and a provider that would raise if called, summary status was `fallback_disabled`; two observations and three limitations rendered. Mocked failure/false-claim tests: `tests/test_management_summary.py`. No live API call. |
| Malformed upload | PASS | A corrupt `.xlsx` returned `rejected` with `DATA.E-PACKAGE` errors; incomplete CSV batch returned `rejected` with 13 errors. The active batch ID was unchanged in both probes. See `tests/data/test_ingestion.py` and `tests/test_application_service.py`. |

## Every PRD MUST feature and acceptance clause

Evidence paths below are repository-relative. A feature marked FAIL can still have passing subclauses.

| ID | Status | Evidence or gap |
| --- | --- | --- |
| F01 behavior | FAIL | `ui/app.py:_upload_controls` assigns domains by fixed controls and activates on one button, but provides no explicit batch preview of selected filenames, sizes and detected domains, or a distinct staged-batch state as the draft requires. Streamlit's uploader may show individual filenames/sizes; that is not a batch preview. |
| F01-AC1 | PASS | `test_valid_csv_and_excel_batches`, `test_equivalent_excel_workbook_is_noop_after_csv_insert`. |
| F01-AC2 | NOT TESTED | Missing/corrupt/oversized cases are tested, but the draft says **every** unsupported/incomplete case; no exhaustive matrix, including password protection, was evidenced. |
| F01-AC3 | PASS | `_upload_controls` calls the service only after the activation button; rejected-upload preservation is tested. |
| F02 behavior | PASS | `data/readers.py`, `domain/validation.py`, `ui/app.py:_feedback`; exact issue fields and counts are covered by ingestion/UI tests. |
| F02-AC1 | NOT TESTED | Numerous field/relationship rules are tested, but no traceable fixture matrix demonstrates **every** Data Contract rule. |
| F02-AC2 | PASS | `test_mixed_valid_invalid_rows_remain_visible_without_partial_acceptance`, `test_rejected_upload_keeps_previous_active_batch`. |
| F02-AC3 | PASS | `test_field_errors_identify_dataset_row_field_and_severity`; UI issue table includes file, sheet, row, field, rule and reason. |
| F03 behavior | PASS | `services/ingestion.py` and validation normalization issues retain original/normalized values; no business-value correction is performed. |
| F03-AC1 | PASS | `test_excel_typed_dates_and_numeric_quantities_normalize_losslessly`, `test_header_alias_and_literal_identifier_are_preserved`. |
| F03-AC2 | PASS | Ambiguous dates, numeric IDs, formulas and fractions rejected in `tests/data/test_ingestion.py`. |
| F03-AC3 | PASS | `test_normalized_duplicate_reports_both_rows`; normalization issue/source fields in `_validation_table`. |
| F04 behavior | PASS | SQLite active-batch replacement is transactional; `tests/data/test_repository.py`. |
| F04-AC1 | PASS | `test_insert_reopen_exact_round_trip_and_relationships`. |
| F04-AC2 | PASS | `test_rejected_batch_and_failed_write_preserve_previous_active_data`. |
| F04-AC3 | PASS | `test_equivalent_reimport_is_noop_and_changed_batch_replaces`. |
| F05 behavior | FAIL | Engine implements the later candidate KPI set, but the original PRD's K01–K07 labels include total output, good output and unplanned downtime rate; those exact named indicators are not all exposed as specified. Business semantics are also provisional. |
| F05-AC1 | PASS | `tests/test_kpi.py` hand-calculated exact assertions for the implemented candidate formulas; this does **not** approve BA-01–BA-05. |
| F05-AC2 | PASS | Zero/empty/N/A cases in `tests/test_kpi.py`. |
| F05-AC3 | PASS | `test_inventory_as_of_carry_forward_and_partial_coverage`; latest eligible per-material snapshot, no daily stock summation. |
| F06 behavior | FAIL | Five later rules are implemented, but the PRD's R01–R04 rule/version/source presentation is not reconciled with the current rule catalog; source references exist in anomaly results but are not exposed in the dashboard anomaly table. |
| F06-AC1 | PASS | `test_each_rule_triggers_with_exact_evidence`, `test_exact_threshold_does_not_trigger`. |
| F06-AC2 | PASS | `domain/anomalies.py:Anomaly` carries rule, entity, values, explanation and `source_refs`; exact evidence asserted in anomaly tests. |
| F06-AC3 | PASS | `test_zero_plan_and_zero_output_skip_undefined_ratios`, `test_missing_as_of_inventory_is_skipped_and_partial`. |
| F07 behavior | FAIL | Overview shows six current candidate cards and trend/alerts, but not all original K01–K05/K07 cards or explicit data coverage required by the draft. The shared UI also has no shift filter. |
| F07-AC1 | PASS | Overview consumes `get_overview_metrics` for cards and series; `test_five_areas_and_filters_render_from_sample_data`, `test_product_filter_and_chart_series_share_the_kpi_population`. |
| F07-AC2 | FAIL | Batch ID and date/line/product filters are visible, but the PRD's shift filter is absent from `ui/app.py`. |
| F07-AC3 | PASS | Empty state and inventory-scope caption in `ui/app.py`; `test_dashboard_empty_state`. |
| F08 behavior | FAIL | Production has trend/line/downtime charts, but lacks the requested K01–K03/K05 presentation, shift control and supporting record rows/source references for R01/R03. |
| F08-AC1 | FAIL | No production detail table exists in `ui/app.py`, so chart totals cannot reconcile with the required visible detail rows. |
| F08-AC2 | NOT TESTED | Engine allows attainment above 100%; no UI assertion or visual evidence confirms a >100% card/chart display. |
| F08-AC3 | PASS | `_metric` labels unavailable values N/A; `_production_trend` labels empty scope; KPI zero/empty tests. |
| F09 behavior | FAIL | Quality shows yield/scrap cards and daily good/scrap chart, but no line comparison, shift control, R02 record details/source references, or separate produced total as requested. |
| F09-AC1 | PASS | Shared series and KPI engine use the same joined data; `test_normal_metrics_and_lineage`, `test_documented_yield_and_scrap_example`. |
| F09-AC2 | PASS | `test_documented_yield_and_scrap_example` and differing-volume KPI fixtures check ratio of sums. |
| F09-AC3 | PASS | `test_zero_output_distinguishes_rates_and_additive_metrics`, `test_positive_output_can_have_zero_good_or_zero_scrap`. |
| F10 behavior | FAIL | As-of material table/coverage exists, but there is no Inventory-only item selector described by the draft. |
| F10-AC1 | PASS | `test_inventory_as_of_carry_forward_and_partial_coverage`. |
| F10-AC2 | PASS | Same test plus `test_inventory_boundary_zero_and_empty_material_selection`; table labels dates/coverage. |
| F10-AC3 | FAIL | Line/product independence is labeled, but the required local item filtering is absent from `ui/app.py`. |
| F11 behavior | FAIL | Seven-sheet export and deterministic summary exist, but the draft calls for the **current optional summary** to be included on regeneration; `export_management_reports` takes only scope and always renders its own deterministic summary. |
| F11-AC1 | PASS | `test_management_files_and_sections_match_analytics`. |
| F11-AC2 | PASS | OpenPyXL opens workbook; `test_renderers_use_supplied_values_and_escape_source_formulas`. |
| F11-AC3 | PASS | `test_no_active_batch_and_stale_payload_are_rejected`, `test_unconfigured_rules_and_empty_production_are_labeled`, renderer-failure/UI warning tests. |
| F11-AC4 | PASS | Report/summary session keys include batch, fingerprint, scope and rule version; `test_dashboard_downloads_are_prepared_on_demand_and_expire_with_filters`. |
| F12 behavior | FAIL | PDF has requested management sections and anomaly preview, but supplies a KPI **definition version**, not the requested KPI definitions; the separate AI draft is not included on report regeneration. |
| F12-AC1 | PASS | `test_management_files_and_sections_match_analytics` checks shared scope, values and sections. |
| F12-AC2 | NOT TESTED | Export and long-filter pagination tests pass; a documented visual review across representative long, empty and full PDF fixtures was not completed in RC1. |
| F12-AC3 | PASS | `test_anomaly_detail_is_complete_in_excel_and_pdf_preview_is_labeled`; renderer-failure tests preserve the other format and data. |

## PRD cross-cutting MUST clauses

| ID | Status | Evidence or gap |
| --- | --- | --- |
| X01 — offline four-domain Excel/CSV workflow and invalid-batch isolation | PASS | `test_csv_upload_to_persisted_kpis_and_anomalies`, `test_excel_upload_uses_same_high_level_service`, report tests, malformed-upload probe. |
| X02 — independent calculations, **all** validation rules, atomicity, anomalies, filters, exports | NOT TESTED | Focused tests cover the named categories, but no complete rule-to-fixture matrix supports the word **all**. |
| X03 — traceability, deterministic non-AI results, no credentials in artifacts, synthetic data | PASS | Source refs in KPI/anomaly results; deterministic synthetic/reimport tests; no key in default settings, `.env.example` placeholders, [security review](../quality/SECURITY_REVIEW.md). Secret absence is bounded to repository artifacts reviewed, not a guarantee about external files. |
| X04 — setup, schemas, definitions, replacement, limits, walkthrough, invalid/offline demo | PASS | [README](../../README.md), [Data Contract](../data/DATA_CONTRACT.md), [KPI Definitions](../data/KPI_DEFINITIONS.md), [Anomaly Rules](../data/ANOMALY_RULES.md), validation and offline probes above. |
| X05 — English/Simplified Chinese document pairs | PASS | Product, data, architecture, decisions, quality and this RC1 record have paired documents; source/document inventory review. This does not imply bilingual UI/reports. |

## Every engineering acceptance criterion

| ID | Status | Evidence or gap |
| --- | --- | --- |
| AC-01 | PASS | Loopback socket and HTTP 200 startup probe above. |
| AC-02 | NOT TESTED | Four-domain accept/reject and diagnostic fields tested; sparse and compressed guards tested. No dense workbook fixture was run, so the full stated fixture set lacks evidence. |
| AC-03 | PASS | `tests/data/test_repository.py` round-trip, failed-write preservation, orphan and fingerprint-tamper tests. |
| AC-04 | PASS | `tests/test_kpi.py` exact candidate-formula fixtures; Completed Orders/Schedule Adherence N/A in the demo and UI test. Business approval remains separate. |
| AC-05 | PASS | `tests/test_anomalies.py` exact, boundary, skipped and simultaneous cases. |
| AC-06 | PASS | `tests/test_dashboard.py` five areas/filter/empty-state; source inspection confirms UI calls services rather than KPI functions. This criterion does not resolve the more specific F07–F10 gaps. |
| AC-07 | PASS | `tests/test_reporting.py` payload equality, long scope pagination, forced one-renderer failures. |
| AC-08 | PASS | Disabled-mode probe and mocked provider/false-claim tests; no live provider call. |
| AC-09 | PASS | Fresh Ruff/pytest results above; focused test modules exist for ingestion, repository, KPI, anomaly and reports. |
| AC-10 | PASS | README, clearly labeled synthetic fixtures, `.env.example`, and [security review](../quality/SECURITY_REVIEW.md). |

## Business acceptance decisions

| ID | Status | Needed before client acceptance |
| --- | --- | --- |
| BA-01 | NOT TESTED | Product owner approves gross/good attainment and cross-product piece comparability. |
| BA-02 | NOT TESTED | Product owner approves final-disposition good/scrap semantics. |
| BA-03 | NOT TESTED | Product owner approves slot/time, inventory and coverage meanings. |
| BA-04 | NOT TESTED | Product owner approves remaining anomaly thresholds, boundaries and severity; earlier per-slot variance choice alone is insufficient. |
| BA-05 | NOT TESTED | Product owner accepts Completed Orders/Schedule Adherence as unavailable or approves a new data contract. |
| BA-06 | NOT TESTED | Charter and PRD intake, persistence, filter and report-format conflicts need dated reconciliation. |
| BA-07 | NOT TESTED | Performance workload, hardware and timing boundary have no agreed benchmark. |
| BA-08 | NOT TESTED | Optional AI delivery and human-review label need owner decision. |

## Release blockers and disposition

1. **PRD mismatch:** F01, F05–F10, F11 and F12 have observed detailed-behavior gaps. Some are original draft details superseded by later implementation tasks, but no dated PRD revision or product-owner disposition resolves them. Do not silently waive them.
2. **Evidence gaps:** F01-AC2, F02-AC1, F08-AC2, F12-AC2, X02 and AC-02 remain NOT TESTED at their stated breadth.
3. **Business gate:** BA-01–BA-08 remain open; the synthetic demo cannot be called client-accepted. Record approved semantics and reconcile charter/PRD, then repeat affected tests and this audit.

**RC1 decision: NO GO for handover.** The application can be demonstrated locally as a synthetic portfolio MVP with the above limitations. No feature code was changed during this release-candidate task.
