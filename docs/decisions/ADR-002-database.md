# ADR-002 — SQLite behind one concrete repository

Date: 2026-09-15  
Status: SQLite mandated by the user; repository/transaction design proposed for review. D05 business import policy remains unresolved.  
Chinese counterpart: [ADR-002-database.zh-CN.md](ADR-002-database.zh-CN.md)

## Context

F04 requires normalized manufacturing data to survive restart, while validation failures must not replace accepted data. The local single-user portfolio needs durable storage without a separate database service. SQLite is now explicitly required; the charter's earlier caution about introducing a database is addressed by this user instruction, not silently overridden by an agent preference.

## Decision

Use one local SQLite database through Python's standard `sqlite3` module and one concrete repository. No ORM, generic repository hierarchy, server database, shared global connection, or connection pool.

The repository owns connections, parameterized SQL, atomic writes, consistent reads, and schema-version checks. Services coordinate operations; domain functions receive records and perform business calculations independently of SQL. Repository SQL does not calculate manufacturing KPIs or anomalies. See [Architecture sections 5–7](../../ARCHITECTURE.md#5-dependency-direction-and-boundary-contracts).

Store normalized data for all four required domains and the provenance/version metadata needed to identify accepted input. Exact relational schema and constraints must follow the future `docs/data/DATA_CONTRACT.md`; no DDL is approved here. Derived analytics are recomputed, not stored as a competing authoritative dataset. Full source files, rejected raw batches, report files, and AI drafts are not archived in the database by default.

Validate/normalize before beginning a write transaction. Commit all affected domain changes and active-dataset metadata together; roll back on failure. Read the active identity and required records within a consistent snapshot, then close the connection before calculation, rendering or external calls. Explicitly choose transaction behavior during implementation instead of relying on version-dependent defaults. SQLite access, transaction control and parameter binding are documented in the [Python sqlite3 reference](https://docs.python.org/3/library/sqlite3.html).

For the PRD's **proposed** whole-batch replacement, removal of the previous active rows and publication of the new rows must be in that same transaction. This explains how to make replacement safe **if D05 is approved**; it does not settle replacement versus merge, duplicate equivalence, or historical retention. A repeated import may be a no-op only according to the agreed identity policy.

On restart, reopen and validate the database schema version. Refuse incompatible versions rather than destructively resetting them. Short explicit versioned schema changes are sufficient initially; no migration framework is selected. On uncertain commit outcome, inspect persisted identity before retrying. Handle locks with a bounded wait and clear recovery guidance.

## Alternatives considered

| Alternative | Disposition |
| --- | --- |
| Streamlit session state only | Rejected: not durable normalized storage across restart. |
| CSV/Excel as the active database | Rejected: does not meet the required SQLite constraint and complicates atomic multi-domain changes. |
| PostgreSQL or a hosted database | Rejected: separate service and credentials without an approved multi-user requirement. |
| ORM / generic repository | Not selected: a concrete SQL module covers the small scope with fewer abstractions. |
| Persist every derived KPI/report | Not selected: creates stale derived copies and history-management scope. |

## Consequences and limits

This provides a compact persistence boundary and makes failure tests practical with temporary on-disk databases. It does not establish multi-user throughput, high availability, automatic backup, inventory transaction history, or enterprise auditing. Database files and generated demo artifacts are local runtime data, not secrets-bearing repository fixtures.

Connections are operation-local; no transaction is held while a user reads a page or an AI request runs. Performance and memory limits await agreed measurements. Persistent identity and definition versions allow services to reject stale view/summary reuse, but do not require a history browser.

## Verification and review triggers

Plan close/reopen tests, injected write failure, cross-domain rollback, consistent-read checks, schema-version refusal, and bounded lock handling. Add duplicate/replacement tests only after D05/Data Contract formalizes their meaning. Do not derive expected business keys from test convenience.

Revisit for an explicitly approved concurrent/multi-site requirement or measured storage limitation. Such a change needs its own rationale and approval. No database file, schema, migration, or production code is created by this ADR.
