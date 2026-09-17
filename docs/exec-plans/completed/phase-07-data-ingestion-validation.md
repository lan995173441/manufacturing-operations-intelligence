# Phase 07 — Data Ingestion and Validation

Status: completed. Sources: `AGENTS.md`, `ARCHITECTURE.md`, `docs/data/DATA_CONTRACT.md` (draft C01–C08). This task explicitly authorizes ingestion/validation implementation; it does not settle unrelated product decisions.

## Outcome and boundaries

Read one four-sheet XLSX or four domain-assigned UTF-8 CSV files. Preserve physical source locations, validate exact schema and contract types, normalize only documented forms, check DATA.R01–R07, and return structured attempt diagnostics. A batch with any error remains rejected; locally valid candidates may continue validation but cannot be partially published. No Streamlit, SQLite write, KPI, dashboard, or anomaly rule.

## Steps

1. Implement strict file readers in `data.readers` with source positions, package/size checks, and explicit parse failures.
2. Implement lossless field conversion and transformation evidence in `domain.normalization`.
3. Implement schema, required values, duplicate, cross-domain and quantity/time checks in `domain.validation`; expose `ValidationIssue` and `ValidationResult` with counts and source references.
4. Coordinate file decoding and validation through a thin `services.ingestion` entry point.
5. Test both packaging formats, malformed and mixed rows, schema/type/range/date failures, post-normalization duplicates, referential failures, source positions, and the synthetic sample batch.
6. Run `ruff check .` and `pytest -q`; record evidence and move this plan to `completed/` on success.

## Acceptance and decisions

- All four canonical business schemas and aliases match the Data Contract; no implicit Pandas NA/type inference.
- Errors contain dataset, row if known, field if known, severity, stable rule code, reason and correction; file-level errors have null row/field.
- Duplicate diagnostics identify both source rows. Relationship errors identify available counterpart rows.
- Any error produces `accepted=False` and no accepted records; valid candidates remain inspectable for this attempt. Parser stoppage reports incomplete evaluation, never success.
- The contract is still a draft: implementation follows its explicitly documented rules for this task without claiming product-owner approval. No import activation or fingerprint/persistence is implemented.

## Validation evidence

- `ruff check .`: all checks passed.
- `pytest -q`: 31 passed.
- The complete Phase 06 synthetic CSV batch passed with 5,220 observed/evaluated/validated records and zero errors.
- Unit tests exercise CSV/XLSX success, missing/duplicate headers, invalid types/dates/negative quantities/missing IDs, mixed valid/invalid rows, post-normalization duplicate locations, DATA.R02–R07, formula and unsafe filename rejection, BOM and aliases, corrupt/blank/malformed inputs, and parser-incomplete reporting.
- No Streamlit, database writes, dashboards, KPI formulas or anomaly rules were added.
