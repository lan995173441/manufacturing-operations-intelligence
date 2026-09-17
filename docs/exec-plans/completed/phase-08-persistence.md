# Phase 08 — SQLite Persistence

Status: completed. Sources: `ARCHITECTURE.md`, `docs/data/DATA_CONTRACT.md` (`0.1-draft`), `AGENTS.md`.

## Scope

Implement one concrete SQLite repository for the four canonical normalized datasets and source/normalization provenance. Accept only a complete successful `ValidationResult`. Replace the active demo dataset atomically; equivalent normalized content is a no-op. Return a coherent read snapshot and provide date, line, product and order filters without exposing SQL to analytics. Do not implement dashboards or KPI calculations.

## Approach

1. Define a small, versioned SQLite schema with batch identity, source metadata, normalization evidence and four dataset tables. Use exact three-place decimal text, business-key uniqueness and foreign keys.
2. Serialize canonical business content per Data Contract section 8 and hash it for equivalence independent of file order and format.
3. Write all records and active-batch identity in one explicit transaction. On failure roll back; never publish a partial batch. Reject unvalidated attempts, schema-version mismatches and incompatible contract versions.
4. Return complete or filtered domain records under one read transaction. Filter production by inclusive business date and optional line/product/order; filter inventory by inclusive snapshot date only.
5. Integrate with temporary on-disk SQLite tests: empty database, insert/reopen/read, filters, replacement/no-op, provenance and relationships, rejected batch/rollback/schema mismatch.
6. Run `ruff check .` and `pytest -q`, record evidence and move this plan to `completed/` on success.

## Decisions and limits

- The user explicitly requests the persistence layer. Data Contract C06 remains a draft product decision; this implementation follows its documented full-replacement behavior without treating it as globally approved.
- Query methods retrieve records only. Order lifecycle metrics, inventory-product joins and SQL KPI aggregation remain outside scope.
- Database creation is explicit through repository initialization. Existing unknown schemas are never reset automatically.

## Validation evidence

- `ruff check .`: all checks passed.
- `pytest -q`: 40 passed, including on-disk SQLite integration tests.
- Empty initialized database returns no active batch. Validated insertion survives connection close/reopen with exact `Decimal` values and four-domain provenance.
- Inclusive date, line, product and order filters return the expected matched production slots; inventory date filtering remains independent.
- Reordered CSV and equivalent XLSX are no-ops; changed content replaces the active batch. Rejected input and a failed constrained write preserve the prior batch.
- SQLite foreign-key checks report no violations. Version mismatch refuses access without resetting data. The full 5,220-row synthetic batch persists and round-trips.
- No SQL was added to analytics, services or UI; no dashboard or KPI code was added.
