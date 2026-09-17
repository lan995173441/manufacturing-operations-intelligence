"""On-disk SQLite integration checks for the canonical repository."""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from manufacturing_operations_intelligence.data.repository import (
    RepositoryError,
    SchemaVersionError,
    SQLiteRepository,
)
from manufacturing_operations_intelligence.domain.validation import SCHEMAS
from manufacturing_operations_intelligence.services.ingestion import (
    ingest_csv_batch,
    ingest_excel_workbook,
)


def _rows() -> dict[str, list[dict[str, str]]]:
    base = {
        "line_id": "LINE-01",
        "shift_id": "DAY",
        "qty_unit": "ea",
    }
    slots = [
        {**base, "production_date": "2025-01-01", "order_id": "MO-001", "product_id": "PRD-001"},
        {
            **base,
            "production_date": "2025-01-02",
            "line_id": "LINE-02",
            "order_id": "MO-002",
            "product_id": "PRD-002",
        },
    ]
    return {
        "production_plan": [
            {**slot, "planned_qty": "100", "planned_production_minutes": "480.000"}
            for slot in slots
        ],
        "production_actual": [
            {**slot, "actual_qty": "90", "runtime_minutes": "450.000", "downtime_minutes": "20.000"}
            for slot in slots
        ],
        "quality": [{**slot, "good_qty": "88", "scrap_qty": "2"} for slot in slots],
        "inventory": [
            {
                "snapshot_date": date,
                "material_id": "MAT-001",
                "qty_unit": "kg",
                "inventory_qty": "120.500",
                "safety_stock": "100.000",
            }
            for date in ("2025-01-01", "2025-01-02")
        ],
    }


def _validated(rows: dict[str, list[dict[str, str]]], *, name_prefix: str = "synthetic"):
    files = {}
    for dataset, records in rows.items():
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(SCHEMAS[dataset]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
        files[dataset] = (f"{name_prefix}_{dataset}.csv", output.getvalue().encode())
    result = ingest_csv_batch(files)
    assert result.accepted, [issue for issue in result.issues if issue.severity == "ERROR"]
    return result


@pytest.fixture
def repository(tmp_path):
    instance = SQLiteRepository(tmp_path / "synthetic.sqlite3")
    instance.initialize()
    return instance


def test_empty_database_has_no_active_batch(repository) -> None:
    assert repository.active_identity() is None
    assert repository.load_batch() is None
    assert repository.query_production() is None
    assert repository.query_inventory() is None
    assert repository.source_manifest() == ()
    assert repository.normalization_evidence() == ()


def test_insert_reopen_exact_round_trip_and_relationships(repository) -> None:
    result = _validated(_rows())
    outcome = repository.replace_demo_dataset(result)
    assert outcome.status == "inserted"
    reopened = SQLiteRepository(repository.path)
    reopened.initialize()
    snapshot = reopened.load_batch()
    assert snapshot is not None
    assert snapshot.identity == outcome.identity
    assert [
        len(snapshot.production_plan),
        len(snapshot.production_actual),
        len(snapshot.quality),
        len(snapshot.inventory),
    ] == [2, 2, 2, 2]
    assert snapshot.production_plan[0].values["planned_qty"] == 100
    assert snapshot.production_actual[0].values["runtime_minutes"] == Decimal("450.000")
    assert snapshot.inventory[0].values["inventory_qty"] == Decimal("120.500")
    assert snapshot.production_plan[0].source_row == 2
    assert {item["dataset"] for item in reopened.source_manifest()} == set(SCHEMAS)
    assert reopened.normalization_evidence()

    plan_keys = {
        (row.values["production_date"], row.values["line_id"], row.values["shift_id"])
        for row in snapshot.production_plan
    }
    for domain in (snapshot.production_actual, snapshot.quality):
        assert {
            (row.values["production_date"], row.values["line_id"], row.values["shift_id"])
            for row in domain
        } == plan_keys
    with sqlite3.connect(repository.path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_production_and_inventory_filters_are_inclusive(repository) -> None:
    repository.replace_demo_dataset(_validated(_rows()))
    for filters in (
        {"start_date": "2025-01-02", "end_date": "2025-01-02"},
        {"line_id": "LINE-02"},
        {"product_id": "PRD-002"},
        {"order_id": "MO-002"},
        {"line_id": "LINE-02", "product_id": "PRD-002", "order_id": "MO-002"},
    ):
        result = repository.query_production(**filters)
        assert result is not None
        assert [
            len(result.production_plan),
            len(result.production_actual),
            len(result.quality),
        ] == [1, 1, 1]
        assert result.production_plan[0].values["order_id"] == "MO-002"
    unmatched = repository.query_production(product_id="PRD-999")
    assert unmatched is not None and unmatched.production_plan == ()
    injected = repository.query_production(order_id="MO-002' OR 1=1 --")
    assert injected is not None and injected.production_plan == ()
    inventory = repository.query_inventory(start_date="2025-01-02", end_date="2025-01-02")
    assert inventory is not None
    assert len(inventory.inventory) == 1
    assert inventory.inventory[0].values["snapshot_date"] == "2025-01-02"
    with pytest.raises(ValueError):
        repository.query_production(start_date="2025-02-30")
    with pytest.raises(ValueError):
        repository.query_inventory(start_date="2025-01-03", end_date="2025-01-02")


def test_equivalent_reimport_is_noop_and_changed_batch_replaces(repository) -> None:
    first = _validated(_rows())
    original = repository.replace_demo_dataset(first)
    reordered = _rows()
    for dataset in reordered:
        reordered[dataset].reverse()
    equivalent = _validated(reordered, name_prefix="same_content_new_filename")
    no_op = repository.replace_demo_dataset(equivalent)
    assert no_op.status == "unchanged"
    assert no_op.identity == original.identity
    assert {source["filename"] for source in repository.source_manifest()} == {
        f"synthetic_{dataset}.csv" for dataset in SCHEMAS
    }

    changed = _rows()
    for dataset in changed:
        changed[dataset] = changed[dataset][1:]
    replacement = repository.replace_demo_dataset(_validated(changed))
    assert replacement.status == "replaced"
    assert replacement.identity.batch_id != original.identity.batch_id
    snapshot = repository.load_batch()
    assert snapshot is not None and len(snapshot.production_plan) == 1
    assert snapshot.production_plan[0].values["order_id"] == "MO-002"
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 1
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_equivalent_excel_workbook_is_noop_after_csv_insert(repository) -> None:
    original = repository.replace_demo_dataset(_validated(_rows()))
    workbook = Workbook()
    workbook.remove(workbook.active)
    for dataset, records in _rows().items():
        sheet = workbook.create_sheet(dataset)
        sheet.append(list(SCHEMAS[dataset]))
        for record in records:
            sheet.append([record[field] for field in SCHEMAS[dataset]])
    output = io.BytesIO()
    workbook.save(output)
    excel_result = ingest_excel_workbook("synthetic.xlsx", output.getvalue())
    assert excel_result.accepted
    no_op = repository.replace_demo_dataset(excel_result)
    assert no_op.status == "unchanged"
    assert no_op.identity == original.identity


def test_rejected_batch_and_failed_write_preserve_previous_active_data(repository) -> None:
    original = repository.replace_demo_dataset(_validated(_rows()))
    invalid = _rows()
    invalid["quality"][0]["good_qty"] = "89"
    output = io.StringIO(newline="")
    files = {}
    for dataset, records in invalid.items():
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(SCHEMAS[dataset]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
        files[dataset] = (f"synthetic_{dataset}.csv", output.getvalue().encode())
    rejected = ingest_csv_batch(files)
    assert not rejected.accepted
    with pytest.raises(RepositoryError):
        repository.replace_demo_dataset(rejected)

    changed = _rows()
    changed["production_plan"][0]["planned_qty"] = "110"
    validated = _validated(changed)
    records = {dataset: tuple(values) for dataset, values in validated.records.items()}
    bad_row = records["production_plan"][0]
    records["production_plan"] = (
        replace(bad_row, values={**bad_row.values, "planned_qty": -1}),
        *records["production_plan"][1:],
    )
    with pytest.raises(RepositoryError):
        repository.replace_demo_dataset(replace(validated, records=records))
    assert repository.active_identity() == original.identity
    assert len(repository.load_batch().production_plan) == 2


def test_unknown_schema_is_not_reset(tmp_path) -> None:
    path = tmp_path / "unknown.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE existing_data (value TEXT)")
        connection.execute("INSERT INTO existing_data VALUES ('keep')")
    repository = SQLiteRepository(path)
    with pytest.raises(SchemaVersionError):
        repository.initialize()
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM existing_data").fetchone()[0] == "keep"


def test_schema_version_mismatch_blocks_access_without_reset(repository) -> None:
    repository.replace_demo_dataset(_validated(_rows()))
    with sqlite3.connect(repository.path) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(SchemaVersionError):
        repository.load_batch()
    with pytest.raises(SchemaVersionError):
        repository.initialize()
    with sqlite3.connect(repository.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 1


@pytest.mark.parametrize("tamper", ["orphan_actual", "changed_quantity"])
def test_persisted_integrity_damage_is_rejected_before_filtered_reads(repository, tamper) -> None:
    repository.replace_demo_dataset(_validated(_rows()))
    with sqlite3.connect(repository.path) as connection:
        if tamper == "orphan_actual":
            connection.execute(
                "UPDATE production_actual SET line_id='ORPHAN' WHERE production_date='2025-01-02'"
            )
        else:
            connection.execute(
                "UPDATE production_actual SET actual_qty=91 WHERE production_date='2025-01-02'"
            )
    with pytest.raises(RepositoryError, match="slot keys|fingerprint"):
        repository.load_batch()
    with pytest.raises(RepositoryError, match="slot keys|fingerprint"):
        repository.query_production(line_id="LINE-01")
    with pytest.raises(RepositoryError, match="slot keys|fingerprint"):
        repository.query_inventory()


def test_complete_synthetic_batch_round_trips_on_disk(repository) -> None:
    root = Path(__file__).resolve().parents[2] / "data" / "samples" / "clean"
    files = {
        dataset: (f"synthetic_{dataset}.csv", (root / f"synthetic_{dataset}.csv").read_bytes())
        for dataset in SCHEMAS
    }
    validated = ingest_csv_batch(files)
    assert validated.accepted
    repository.replace_demo_dataset(validated)
    reopened = SQLiteRepository(repository.path)
    result = reopened.load_batch()
    assert result is not None
    assert (
        len(result.production_plan) == len(result.production_actual) == len(result.quality) == 540
    )
    assert len(result.inventory) == 3600
    assert len(reopened.query_production(line_id="LINE-02").production_plan) == 180
