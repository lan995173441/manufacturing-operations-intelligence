# UI review — P0 corrections

Status: completed; browser visual verification limited as recorded below. Chinese counterpart: [ui-review-p0.zh-CN.md](ui-review-p0.zh-CN.md).

Scope: inspect the five Streamlit areas, rank ten UX improvements in a bilingual review, and implement only P0 corrections in the UI. No business-rule, service, persistence, dependency or formula changes.

Sources: AGENTS.md, ARCHITECTURE.md, PRD.md, existing UI, service result contracts and dashboard tests. UI_SPEC.md is absent; this review does not invent an approved UI specification. Historical V0 document status is not current implementation status.

1. Inspect normal, empty, incomplete-alert and import-feedback states; capture browser evidence where available.
2. P0-01: distinguish disabled, unsupported, empty and incomplete checks from a completed no-alert result; expose skipped-check reasons.
3. P0-02: state that demo/upload activation replaces all four datasets, and require a local acknowledgement only when data is already active.
4. P0-03: expose validation counts and complete source locations plus original/normalized values; keep normalization details collapsed; avoid raw persistence exceptions in the main message.
5. Add regression tests for these user-visible behaviors, run the full suite and Ruff, and visually verify changed states.
6. Record evidence, verify lower-layer file hashes are unchanged, and move this plan and its Chinese counterpart to completed.

Assumptions: P0 means misleading operational conclusions, unexpected dataset replacement, or inability to audit/correct an import. P1/P2 improvements are recommendations only. Acknowledgement is a UI interaction, not a change to atomic replacement or validation policy. No default manufacturing threshold will be invented.

## Completion evidence

- Ten ranked improvements documented in [UI_REVIEW](../../design/UI_REVIEW.md); UX-01–03 implemented, UX-04–10 deferred.
- Dashboard regression: 12 passed in 13.53s (10 new cases). Full suite: 103 passed in 17.76s. Ruff: all checks passed.
- AppTest walkthrough covers five areas with zero exceptions. Lower-layer SHA-256 hashes are unchanged.
- Local HTTP response: 200. Chrome launch was blocked by the sandbox's process-port restriction, so screenshot/pixel-level verification could not be completed; this limitation is recorded in both review versions.
- Changed application code: `src/manufacturing_operations_intelligence/ui/app.py` only. Added tests in `tests/test_dashboard.py`; added bilingual review and execution-plan documents. No new dependencies or business behavior.
