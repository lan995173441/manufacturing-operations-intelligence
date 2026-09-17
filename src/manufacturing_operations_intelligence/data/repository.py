"""Single-file SQLite persistence for validated manufacturing batches.

This module owns SQL and record retrieval. It never computes business metrics.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CONTRACT_VERSION = "0.1-draft"
COMMON = ("production_date", "line_id", "shift_id", "order_id", "product_id", "qty_unit")
FIELDS = {
    "production_plan": (*COMMON, "planned_qty", "planned_production_minutes"),
    "production_actual": (*COMMON, "actual_qty", "runtime_minutes", "downtime_minutes"),
    "quality": (*COMMON, "good_qty", "scrap_qty"),
    "inventory": ("snapshot_date", "material_id", "qty_unit", "inventory_qty", "safety_stock"),
}
KEYS = {
    "production_plan": COMMON[:3],
    "production_actual": COMMON[:3],
    "quality": COMMON[:3],
    "inventory": ("snapshot_date", "material_id"),
}
DECIMALS = {
    "production_plan": ("planned_production_minutes",),
    "production_actual": ("runtime_minutes", "downtime_minutes"),
    "quality": (),
    "inventory": ("inventory_qty", "safety_stock"),
}
COUNTS = {
    "production_plan": ("planned_qty",),
    "production_actual": ("actual_qty",),
    "quality": ("good_qty", "scrap_qty"),
    "inventory": (),
}

_SCHEMA = """
CREATE TABLE batches (
 batch_id TEXT PRIMARY KEY, contract_version TEXT NOT NULL,
 fingerprint TEXT NOT NULL, imported_at_utc TEXT NOT NULL
);
CREATE TABLE active_batch (
 singleton INTEGER PRIMARY KEY CHECK (singleton=1),
 batch_id TEXT NOT NULL REFERENCES batches(batch_id)
);
CREATE TABLE sources (
 source_id TEXT PRIMARY KEY,
 batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
 dataset TEXT NOT NULL CHECK(dataset IN
  ('production_plan','production_actual','quality','inventory')),
 filename TEXT NOT NULL, sha256 TEXT NOT NULL, sheet TEXT,
 UNIQUE(batch_id,dataset), UNIQUE(batch_id,source_id)
);
CREATE TABLE normalization_evidence (
 batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
 source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
 source_row INTEGER, dataset TEXT NOT NULL, field TEXT,
 action_code TEXT NOT NULL, original TEXT, normalized TEXT
);
CREATE TABLE production_plan (
 batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
 source_id TEXT NOT NULL, source_row INTEGER NOT NULL CHECK(source_row>=2),
 production_date TEXT NOT NULL, line_id TEXT NOT NULL, shift_id TEXT NOT NULL,
 order_id TEXT NOT NULL, product_id TEXT NOT NULL,
 qty_unit TEXT NOT NULL CHECK(qty_unit='ea'),
 planned_qty INTEGER NOT NULL CHECK(planned_qty>=0),
 planned_production_minutes TEXT NOT NULL,
 PRIMARY KEY(batch_id,production_date,line_id,shift_id),
 FOREIGN KEY(batch_id,source_id) REFERENCES sources(batch_id,source_id) ON DELETE CASCADE
);
CREATE TABLE production_actual (
 batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
 source_id TEXT NOT NULL, source_row INTEGER NOT NULL CHECK(source_row>=2),
 production_date TEXT NOT NULL, line_id TEXT NOT NULL, shift_id TEXT NOT NULL,
 order_id TEXT NOT NULL, product_id TEXT NOT NULL,
 qty_unit TEXT NOT NULL CHECK(qty_unit='ea'),
 actual_qty INTEGER NOT NULL CHECK(actual_qty>=0),
 runtime_minutes TEXT NOT NULL, downtime_minutes TEXT NOT NULL,
 PRIMARY KEY(batch_id,production_date,line_id,shift_id),
 FOREIGN KEY(batch_id,source_id) REFERENCES sources(batch_id,source_id) ON DELETE CASCADE,
 FOREIGN KEY(batch_id,production_date,line_id,shift_id)
  REFERENCES production_plan(batch_id,production_date,line_id,shift_id) ON DELETE CASCADE
);
CREATE TABLE quality (
 batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
 source_id TEXT NOT NULL, source_row INTEGER NOT NULL CHECK(source_row>=2),
 production_date TEXT NOT NULL, line_id TEXT NOT NULL, shift_id TEXT NOT NULL,
 order_id TEXT NOT NULL, product_id TEXT NOT NULL,
 qty_unit TEXT NOT NULL CHECK(qty_unit='ea'),
 good_qty INTEGER NOT NULL CHECK(good_qty>=0),
 scrap_qty INTEGER NOT NULL CHECK(scrap_qty>=0),
 PRIMARY KEY(batch_id,production_date,line_id,shift_id),
 FOREIGN KEY(batch_id,source_id) REFERENCES sources(batch_id,source_id) ON DELETE CASCADE,
 FOREIGN KEY(batch_id,production_date,line_id,shift_id)
  REFERENCES production_plan(batch_id,production_date,line_id,shift_id) ON DELETE CASCADE
);
CREATE TABLE inventory (
 batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
 source_id TEXT NOT NULL, source_row INTEGER NOT NULL CHECK(source_row>=2),
 snapshot_date TEXT NOT NULL, material_id TEXT NOT NULL,
 qty_unit TEXT NOT NULL CHECK(qty_unit IN ('ea','kg','m','l')),
 inventory_qty TEXT NOT NULL, safety_stock TEXT NOT NULL,
 PRIMARY KEY(batch_id,snapshot_date,material_id),
 FOREIGN KEY(batch_id,source_id) REFERENCES sources(batch_id,source_id) ON DELETE CASCADE
);
CREATE INDEX plan_filter ON production_plan
 (batch_id,production_date,line_id,product_id,order_id);
CREATE INDEX inventory_date ON inventory(batch_id,snapshot_date);
PRAGMA user_version=1;
"""


class RepositoryError(RuntimeError):
    """The requested storage operation cannot complete safely."""


class SchemaVersionError(RepositoryError):
    """Database schema does not match this repository version."""


class RepositoryBusy(RepositoryError):
    """Database is locked and an explicit retry may succeed."""


@dataclass(frozen=True)
class BatchIdentity:
    batch_id: str
    contract_version: str
    fingerprint: str
    imported_at_utc: str


@dataclass(frozen=True)
class StoredRow:
    source_id: str
    source_row: int
    values: dict[str, Any]


@dataclass(frozen=True)
class ProductionSnapshot:
    identity: BatchIdentity
    production_plan: tuple[StoredRow, ...]
    production_actual: tuple[StoredRow, ...]
    quality: tuple[StoredRow, ...]


@dataclass(frozen=True)
class InventorySnapshot:
    identity: BatchIdentity
    inventory: tuple[StoredRow, ...]


@dataclass(frozen=True)
class BatchSnapshot:
    identity: BatchIdentity
    production_plan: tuple[StoredRow, ...]
    production_actual: tuple[StoredRow, ...]
    quality: tuple[StoredRow, ...]
    inventory: tuple[StoredRow, ...]


@dataclass(frozen=True)
class ReplaceOutcome:
    status: str  # inserted, replaced, unchanged
    identity: BatchIdentity


def _business_values(dataset: str, values: Mapping[str, Any]) -> dict[str, Any]:
    if set(values) != set(FIELDS[dataset]):
        raise RepositoryError(f"{dataset} record fields do not match the canonical schema.")
    clean = {}
    for field in FIELDS[dataset]:
        value = values[field]
        if field in DECIMALS[dataset]:
            if not isinstance(value, Decimal) or not value.is_finite():
                raise RepositoryError(f"{dataset}.{field} requires a finite Decimal.")
            if value != value.quantize(Decimal("0.001")):
                raise RepositoryError(f"{dataset}.{field} exceeds three decimal places.")
            clean[field] = f"{value:.3f}"
        elif field in COUNTS[dataset]:
            if isinstance(value, bool) or not isinstance(value, int):
                raise RepositoryError(f"{dataset}.{field} requires an integer.")
            clean[field] = value
        elif isinstance(value, str):
            clean[field] = value
        else:
            raise RepositoryError(f"{dataset}.{field} requires canonical text.")
    return clean


def _fingerprint_records(records: Mapping[str, tuple[Any, ...]]) -> str:
    datasets = {}
    for dataset in sorted(FIELDS):
        ordered = sorted(
            records[dataset],
            key=lambda row: tuple(row.values[field] for field in KEYS[dataset]),
        )
        datasets[dataset] = [_business_values(dataset, row.values) for row in ordered]
    payload = {"contract_version": CONTRACT_VERSION, "datasets": datasets}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fingerprint(batch: Any) -> str:
    return _fingerprint_records(batch.records)


def _check_batch(batch: Any) -> None:
    if not batch.accepted or batch.error_count or set(batch.records) != set(FIELDS):
        raise RepositoryError("Only a complete error-free validation result may be stored.")
    sources = {source.dataset: source for source in batch.sources}
    if set(sources) != set(FIELDS) or len(batch.sources) != len(FIELDS):
        raise RepositoryError("Exactly one source per canonical dataset is required.")
    for dataset, records in batch.records.items():
        if not records:
            raise RepositoryError(f"{dataset} has no validated rows.")
        keys = []
        for row in records:
            if row.source_id != sources[dataset].source_id or row.source_row < 2:
                raise RepositoryError(f"{dataset} has invalid source provenance.")
            _business_values(dataset, row.values)
            keys.append(tuple(row.values[field] for field in KEYS[dataset]))
        if len(set(keys)) != len(keys):
            raise RepositoryError(f"{dataset} has duplicate business keys.")
    production_keys = [
        {tuple(row.values[field] for field in KEYS[dataset]) for row in batch.records[dataset]}
        for dataset in ("production_plan", "production_actual", "quality")
    ]
    if not production_keys[0] == production_keys[1] == production_keys[2]:
        raise RepositoryError("Production datasets have inconsistent slot keys.")


def _date_bounds(start_date: str | None, end_date: str | None) -> None:
    for name, value in (("start_date", start_date), ("end_date", end_date)):
        if value is None:
            continue
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be ISO YYYY-MM-DD.") from exc
        if parsed.isoformat() != value:
            raise ValueError(f"{name} must be ISO YYYY-MM-DD.")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must not exceed end_date.")


class SQLiteRepository:
    """Short-lived connections and atomic replacement for one local SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=2.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=2000")
        try:
            yield connection
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise RepositoryBusy("Database is busy; retry after its writer completes.") from exc
            raise
        finally:
            connection.close()

    @staticmethod
    def _assert_schema(connection: sqlite3.Connection) -> None:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise SchemaVersionError(
                f"Database schema version {version} is incompatible with {SCHEMA_VERSION}."
            )
        present = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required = {*FIELDS, "batches", "active_batch", "sources", "normalization_evidence"}
        if not required <= present:
            raise SchemaVersionError("Database is missing required tables; no reset performed.")

    def initialize(self) -> None:
        """Create a fresh schema; never reset an unknown existing database."""
        with self._connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == SCHEMA_VERSION:
                self._assert_schema(connection)
                return
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version != 0 or tables:
                raise SchemaVersionError("Existing database schema is unknown; no reset performed.")
            connection.executescript("BEGIN IMMEDIATE;\n" + _SCHEMA + "\nCOMMIT;")

    @staticmethod
    def _active(connection: sqlite3.Connection) -> BatchIdentity | None:
        row = connection.execute(
            "SELECT b.batch_id,b.contract_version,b.fingerprint,b.imported_at_utc "
            "FROM active_batch a JOIN batches b ON b.batch_id=a.batch_id "
            "WHERE a.singleton=1"
        ).fetchone()
        if row is None:
            return None
        identity = BatchIdentity(**dict(row))
        if identity.contract_version != CONTRACT_VERSION:
            raise RepositoryError("Active batch has an unsupported Data Contract version.")
        return identity

    def active_identity(self) -> BatchIdentity | None:
        """An initialized empty database has no active identity."""
        with self._connection() as connection:
            self._assert_schema(connection)
            return self._active(connection)

    def replace_demo_dataset(self, batch: Any) -> ReplaceOutcome:
        """Insert validated records and switch the active batch in one transaction."""
        _check_batch(batch)
        fingerprint = _fingerprint(batch)
        try:
            with self._connection() as connection:
                self._assert_schema(connection)
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    current = self._active(connection)
                    if current and current.fingerprint == fingerprint:
                        connection.execute("COMMIT")
                        return ReplaceOutcome("unchanged", current)
                    if current and current.batch_id == batch.attempt_id:
                        raise RepositoryError(
                            "Attempt ID already identifies different active content."
                        )
                    imported_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    connection.execute(
                        "INSERT INTO batches VALUES (?,?,?,?)",
                        (batch.attempt_id, CONTRACT_VERSION, fingerprint, imported_at),
                    )
                    for source in batch.sources:
                        connection.execute(
                            "INSERT INTO sources VALUES (?,?,?,?,?,?)",
                            (
                                source.source_id,
                                batch.attempt_id,
                                source.dataset,
                                source.filename,
                                source.sha256,
                                source.sheet,
                            ),
                        )
                    for dataset, records in batch.records.items():
                        columns = ("batch_id", "source_id", "source_row", *FIELDS[dataset])
                        placeholders = ",".join("?" for _ in columns)
                        sql = f"INSERT INTO {dataset} ({','.join(columns)}) VALUES ({placeholders})"
                        parameters = []
                        for row in records:
                            values = _business_values(dataset, row.values)
                            parameters.append(
                                (
                                    batch.attempt_id,
                                    row.source_id,
                                    row.source_row,
                                    *(values[name] for name in FIELDS[dataset]),
                                )
                            )
                        connection.executemany(sql, parameters)
                    for issue in batch.issues:
                        if issue.severity == "INFO" and issue.source_id:
                            connection.execute(
                                "INSERT INTO normalization_evidence VALUES (?,?,?,?,?,?,?,?)",
                                (
                                    batch.attempt_id,
                                    issue.source_id,
                                    issue.row,
                                    issue.dataset,
                                    issue.field,
                                    issue.code,
                                    issue.original,
                                    issue.normalized,
                                ),
                            )
                    connection.execute(
                        "INSERT INTO active_batch(singleton,batch_id) VALUES (1,?) "
                        "ON CONFLICT(singleton) DO UPDATE SET batch_id=excluded.batch_id",
                        (batch.attempt_id,),
                    )
                    if current:
                        connection.execute(
                            "DELETE FROM batches WHERE batch_id=?", (current.batch_id,)
                        )
                    connection.execute("COMMIT")
                    return ReplaceOutcome(
                        "replaced" if current else "inserted",
                        BatchIdentity(batch.attempt_id, CONTRACT_VERSION, fingerprint, imported_at),
                    )
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise RepositoryBusy("Database is busy; retry after its writer completes.") from exc
            raise RepositoryError("SQLite write failed; prior active batch is retained.") from exc
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(
                "Database constraints rejected the batch; prior data is retained."
            ) from exc

    @staticmethod
    def _decode(dataset: str, row: sqlite3.Row) -> StoredRow:
        values = {field: row[field] for field in FIELDS[dataset]}
        for field in DECIMALS[dataset]:
            try:
                values[field] = Decimal(values[field])
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise RepositoryError(
                    f"Active {dataset}.{field} is not a valid stored decimal."
                ) from exc
        return StoredRow(row["source_id"], row["source_row"], values)

    @staticmethod
    def _production_rows(
        connection: sqlite3.Connection,
        batch_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        line_id: str | None = None,
        product_id: str | None = None,
        order_id: str | None = None,
    ) -> tuple[tuple[StoredRow, ...], tuple[StoredRow, ...], tuple[StoredRow, ...]]:
        conditions = ["p.batch_id=?"]
        params: list[str] = [batch_id]
        for column, value, operator in (
            ("production_date", start_date, ">="),
            ("production_date", end_date, "<="),
            ("line_id", line_id, "="),
            ("product_id", product_id, "="),
            ("order_id", order_id, "="),
        ):
            if value is not None:
                conditions.append(f"p.{column}{operator}?")
                params.append(value)
        where = " AND ".join(conditions)
        order = "ORDER BY p.production_date,p.line_id,p.shift_id"
        results = []
        for dataset in ("production_plan", "production_actual", "quality"):
            if dataset == "production_plan":
                sql = f"SELECT p.* FROM production_plan p WHERE {where} {order}"
            else:
                sql = (
                    f"SELECT d.* FROM {dataset} d JOIN production_plan p "
                    "ON d.batch_id=p.batch_id AND d.production_date=p.production_date "
                    "AND d.line_id=p.line_id AND d.shift_id=p.shift_id "
                    f"WHERE {where} {order}"
                )
            results.append(
                tuple(
                    SQLiteRepository._decode(dataset, row)
                    for row in connection.execute(sql, params)
                )
            )
        return results[0], results[1], results[2]

    @staticmethod
    def _inventory_rows(
        connection: sqlite3.Connection,
        batch_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[StoredRow, ...]:
        conditions = ["batch_id=?"]
        params = [batch_id]
        if start_date is not None:
            conditions.append("snapshot_date>=?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("snapshot_date<=?")
            params.append(end_date)
        sql = (
            "SELECT * FROM inventory WHERE "
            + " AND ".join(conditions)
            + " ORDER BY snapshot_date,material_id"
        )
        return tuple(
            SQLiteRepository._decode("inventory", row) for row in connection.execute(sql, params)
        )

    @staticmethod
    def _complete_batch(connection: sqlite3.Connection, identity: BatchIdentity) -> BatchSnapshot:
        records = {
            dataset: tuple(
                SQLiteRepository._decode(dataset, row)
                for row in connection.execute(
                    f"SELECT * FROM {dataset} WHERE batch_id=? ORDER BY {','.join(KEYS[dataset])}",
                    (identity.batch_id,),
                )
            )
            for dataset in FIELDS
        }
        keys = [
            {tuple(row.values[field] for field in KEYS[dataset]) for row in records[dataset]}
            for dataset in ("production_plan", "production_actual", "quality")
        ]
        if not keys[0] == keys[1] == keys[2]:
            raise RepositoryError("Active production datasets have inconsistent slot keys.")
        source_ids = {
            row["dataset"]: row["source_id"]
            for row in connection.execute(
                "SELECT dataset,source_id FROM sources WHERE batch_id=?", (identity.batch_id,)
            )
        }
        if set(source_ids) != set(FIELDS) or any(
            row.source_id != source_ids[dataset]
            for dataset in FIELDS for row in records[dataset]
        ):
            raise RepositoryError("Active batch source references are inconsistent.")
        if _fingerprint_records(records) != identity.fingerprint:
            raise RepositoryError("Active batch content differs from its stored fingerprint.")
        return BatchSnapshot(
            identity,
            records["production_plan"],
            records["production_actual"],
            records["quality"],
            records["inventory"],
        )

    def load_batch(self) -> BatchSnapshot | None:
        """Read active identity and all four domains in one SQLite read snapshot."""
        with self._connection() as connection:
            self._assert_schema(connection)
            try:
                connection.execute("BEGIN")
                identity = self._active(connection)
                if identity is None:
                    connection.execute("COMMIT")
                    return None
                batch = self._complete_batch(connection, identity)
                connection.execute("COMMIT")
                return batch
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def query_production(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        line_id: str | None = None,
        product_id: str | None = None,
        order_id: str | None = None,
    ) -> ProductionSnapshot | None:
        """Retrieve matching production slots; business-date bounds are inclusive."""
        _date_bounds(start_date, end_date)
        with self._connection() as connection:
            self._assert_schema(connection)
            try:
                connection.execute("BEGIN")
                identity = self._active(connection)
                if identity is None:
                    connection.execute("COMMIT")
                    return None
                self._complete_batch(connection, identity)
                records = self._production_rows(
                    connection,
                    identity.batch_id,
                    start_date=start_date,
                    end_date=end_date,
                    line_id=line_id,
                    product_id=product_id,
                    order_id=order_id,
                )
                connection.execute("COMMIT")
                return ProductionSnapshot(identity, *records)
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def query_inventory(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> InventorySnapshot | None:
        """Retrieve material observations by inclusive snapshot-date range."""
        _date_bounds(start_date, end_date)
        with self._connection() as connection:
            self._assert_schema(connection)
            try:
                connection.execute("BEGIN")
                identity = self._active(connection)
                if identity is None:
                    connection.execute("COMMIT")
                    return None
                self._complete_batch(connection, identity)
                rows = self._inventory_rows(
                    connection, identity.batch_id, start_date=start_date, end_date=end_date
                )
                connection.execute("COMMIT")
                return InventorySnapshot(identity, rows)
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def source_manifest(self) -> tuple[dict[str, Any], ...]:
        """Return active source provenance or an empty tuple."""
        with self._connection() as connection:
            self._assert_schema(connection)
            try:
                connection.execute("BEGIN")
                identity = self._active(connection)
                rows = (
                    ()
                    if identity is None
                    else tuple(
                        dict(row)
                        for row in connection.execute(
                            "SELECT source_id,dataset,filename,sha256,sheet FROM sources "
                            "WHERE batch_id=? ORDER BY dataset",
                            (identity.batch_id,),
                        )
                    )
                )
                connection.execute("COMMIT")
                return rows
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def normalization_evidence(self) -> tuple[dict[str, Any], ...]:
        """Return allowed conversion evidence for the active batch."""
        with self._connection() as connection:
            self._assert_schema(connection)
            try:
                connection.execute("BEGIN")
                identity = self._active(connection)
                rows = (
                    ()
                    if identity is None
                    else tuple(
                        dict(row)
                        for row in connection.execute(
                            "SELECT source_id,source_row,dataset,field,action_code,"
                            "original,normalized FROM normalization_evidence "
                            "WHERE batch_id=? ORDER BY dataset,source_row",
                            (identity.batch_id,),
                        )
                    )
                )
                connection.execute("COMMIT")
                return rows
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
