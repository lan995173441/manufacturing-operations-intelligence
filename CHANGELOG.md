# Changelog

Chinese counterpart: [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md).

## v1.0.0 — 2026-09-20

- Released the local, synthetic-data portfolio MVP after explicit release-approver acceptance of the documented outstanding risks.
- No feature, KPI, data-contract, or architecture changes were made for the final version.
- Known exceptions remain: product-owner decisions BA-01–BA-08 are not recorded, no UAT artifact is present in the repository, and no approved performance target is recorded. This release is limited to the documented local demonstration scope and is not a production MES, compliance tool, or confidential-data service.

## v1.0.0-rc.1 — 2026-09-20

- Aligned package and runtime metadata to the PEP 440 release-candidate version `1.0.0rc1`.
- Added release-freeze fixes for current-summary report regeneration, report KPI-definition visibility, staged upload metadata, shared shift/material filters, and dashboard evidence detail.
- Added a versioned QA test plan and regression coverage. Product-owner decisions BA-01–BA-08 remain open.

## RC1 candidate — 2026-09-17

- Froze feature work and audited the PRD MUST clauses and acceptance criteria. Results and evidence: [RC1 release checklist](docs/release/RELEASE_CHECKLIST.md).
- Re-ran the complete suite (138 passed) and Ruff (passed). Verified loopback startup, the 90-day synthetic batch, Excel/PDF exports, AI-disabled fallback, and malformed-upload rejection.
- No application behavior or business formula was changed for RC1.
- **Handover blocked:** several detailed PRD clauses are unmet or lack complete evidence; product-owner decisions BA-01–BA-08 remain open. This candidate is an engineering-validated synthetic portfolio demonstration, not client acceptance.
