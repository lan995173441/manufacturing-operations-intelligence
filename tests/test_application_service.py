"""Integration evidence for the application service workflow."""

from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from manufacturing_operations_intelligence.data.repository import RepositoryError
from manufacturing_operations_intelligence.data.synthetic import (
    generate_synthetic_data,
    write_synthetic_csv,
)
from manufacturing_operations_intelligence.domain.analytics import KpiScope
from manufacturing_operations_intelligence.domain.anomalies import (
    HIGH_PRODUCTION_VARIANCE,
    LOW_ATTAINMENT,
    LOW_INVENTORY,
)
from manufacturing_operations_intelligence.services.application import (
    ApplicationServiceError,
    ManufacturingApplicationService,
)


@pytest.fixture(scope="module")
def synthetic_bundle():
    return generate_synthetic_data()


def _csv_batch(bundle, directory: Path) -> dict[str, tuple[str, bytes]]:
    paths = write_synthetic_csv(bundle, directory)
    return {dataset: (path.name, path.read_bytes()) for dataset, path in paths.items()}


def _one_slot_workbook(bundle) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for dataset, frame in bundle.datasets().items():
        sheet = workbook.create_sheet(dataset)
        sheet.append(list(frame.columns))
        sheet.append([str(value) for value in frame.iloc[0].tolist()])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_csv_upload_to_persisted_kpis_and_anomalies(tmp_path: Path, synthetic_bundle) -> None:
    database = tmp_path / "synthetic.sqlite3"
    service = ManufacturingApplicationService.from_path(
        database, downtime_above_minutes=Decimal("120")
    )
    assert service.get_available_scope() is None
    empty_scope = KpiScope("2025-01-01", "2025-01-01")
    assert service.get_overview_metrics(empty_scope).status == "no_active_batch"
    assert service.get_anomalies(empty_scope).status == "no_active_batch"

    files = _csv_batch(synthetic_bundle, tmp_path / "input")
    upload = service.process_uploaded_data(csv_files=files)
    assert upload.status == "accepted"
    assert upload.validation.accepted
    assert upload.validation.normalization_action_count > 0
    assert upload.validation.total_observed_rows == 90 * 3 * 2 * 3 + 90 * 40
    assert upload.persistence.status == "inserted"
    batch_id = upload.persistence.identity.batch_id
    assert service.get_available_scope() == KpiScope("2025-01-01", "2025-03-31")
    options = service.get_filter_options()
    assert options.identity.batch_id == batch_id
    assert options.line_ids == ("LINE-01", "LINE-02", "LINE-03")
    assert options.shift_ids == ("DAY", "NIGHT")
    assert len(options.product_ids) == 20
    assert len(options.material_ids) == 40

    day = synthetic_bundle.scenarios.underperformance_dates[0].isoformat()
    scope = KpiScope(day, day, line_ids=("LINE-02",))
    overview = service.get_overview_metrics(scope)
    production = service.get_production_analysis(scope)
    quality = service.get_quality_analysis(scope)
    assert overview.status == production.status == quality.status == "available"
    assert overview.identity.batch_id == production.identity.batch_id == batch_id
    assert set(production.metrics) == {"KPI-PA", "KPI-TD", "KPI-OL"}
    assert set(quality.metrics) == {"KPI-GY", "KPI-SR"}
    attainment = production.metrics["KPI-PA"]
    assert attainment.status == "valid"
    assert attainment.value < 90
    assert attainment.batch_id == batch_id
    assert attainment.source_refs
    assert overview.metrics["KPI-PA"] == attainment

    detected = service.get_anomalies(scope)
    assert detected.status == "available"
    assert detected.identity.batch_id == batch_id
    assert detected.detection.batch_id == batch_id
    assert {item.type for item in detected.detection.anomalies} >= {
        LOW_ATTAINMENT,
        HIGH_PRODUCTION_VARIANCE,
    }

    stock_day = synthetic_bundle.scenarios.low_inventory_dates[0].isoformat()
    stock_scope = KpiScope(
        stock_day,
        stock_day,
        material_ids=synthetic_bundle.scenarios.low_inventory_material_ids,
    )
    inventory = service.get_inventory_analysis(stock_scope)
    assert inventory.metrics["KPI-IR"].status == "valid"
    assert inventory.metrics["KPI-IR"].value == 4
    stock_alerts = service.get_anomalies(stock_scope).detection
    assert sum(item.type == LOW_INVENTORY for item in stock_alerts.anomalies) == 4

    reopened = ManufacturingApplicationService.from_path(
        database, downtime_above_minutes=Decimal("120")
    )
    assert reopened.get_overview_metrics(scope).identity.batch_id == batch_id
    assert reopened.get_overview_metrics(scope).metrics["KPI-PA"] == attainment
    assert reopened.process_uploaded_data(csv_files=files).persistence.status == "unchanged"


def test_rejected_upload_keeps_previous_active_batch(tmp_path: Path, synthetic_bundle) -> None:
    service = ManufacturingApplicationService.from_path(tmp_path / "rejected.sqlite3")
    files = _csv_batch(synthetic_bundle, tmp_path / "input")
    first = service.process_uploaded_data(csv_files=files)
    before = first.persistence.identity
    bad_files = dict(files)
    filename, content = files["quality"]
    bad_files["quality"] = (filename, content.splitlines(keepends=True)[0])
    rejected = service.process_uploaded_data(csv_files=bad_files)
    assert rejected.status == "rejected"
    assert not rejected.validation.accepted
    assert rejected.validation.error_count > 0
    assert rejected.persistence is None
    scope = KpiScope("2025-01-01", "2025-01-01")
    assert service.get_overview_metrics(scope).identity == before
    assert service.get_anomalies(scope).status == "rules_not_configured"


def test_excel_upload_uses_same_high_level_service(tmp_path: Path, synthetic_bundle) -> None:
    service = ManufacturingApplicationService.from_path(
        tmp_path / "excel.sqlite3", downtime_above_minutes=Decimal("30")
    )
    workbook = _one_slot_workbook(synthetic_bundle)
    result = service.process_uploaded_data(workbook=("synthetic.xlsx", workbook))
    assert result.status == "accepted"
    assert result.validation.accepted
    assert all(len(rows) == 1 for rows in result.validation.records.values())
    scope = KpiScope("2025-01-01", "2025-01-01")
    assert service.get_production_analysis(scope).metrics["KPI-PA"].status == "valid"
    assert service.get_anomalies(scope).status == "available"


def test_persistence_error_is_distinct_from_validation_failure(
    tmp_path: Path, synthetic_bundle, monkeypatch
) -> None:
    service = ManufacturingApplicationService.from_path(tmp_path / "write.sqlite3")
    files = _csv_batch(synthetic_bundle, tmp_path / "input")

    def fail_write(_batch):
        raise RepositoryError("Synthetic database write failure: private-location.")

    monkeypatch.setattr(service._repository, "replace_demo_dataset", fail_write)
    result = service.process_uploaded_data(csv_files=files)
    assert result.status == "persistence_failed"
    assert result.validation.accepted
    assert result.persistence is None
    assert result.persistence_error == (
        "The validated upload could not be saved to the local data store."
    )
    assert "private-location" not in repr(result)
    assert service.get_available_scope() is None


def test_service_rejects_missing_or_conflicting_upload_modes(tmp_path: Path) -> None:
    service = ManufacturingApplicationService.from_path(tmp_path / "request.sqlite3")
    with pytest.raises(ApplicationServiceError):
        service.process_uploaded_data()
    with pytest.raises(ApplicationServiceError):
        service.process_uploaded_data(csv_files={}, workbook=("synthetic.xlsx", b""))


def test_builtin_synthetic_demo_can_be_activated(tmp_path: Path) -> None:
    service = ManufacturingApplicationService.from_path(tmp_path / "demo.sqlite3")
    result = service.load_sample_data()
    assert result.status == "accepted"
    assert service.get_filter_options().start_date == "2025-01-01"
