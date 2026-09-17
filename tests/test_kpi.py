"""Hand-calculated KPI fixtures, including unavailable and invalid-data states."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

import pytest

from manufacturing_operations_intelligence.domain.analytics import (
    KpiScope,
    calculate_dashboard_data,
    calculate_kpis,
    completed_orders,
    good_yield,
    inventory_risk,
    output_by_production_line,
    production_attainment,
    schedule_adherence,
    scrap_rate,
    total_downtime,
)

SCOPE = KpiScope("2026-01-01", "2026-01-02")


def _row(dataset: str, number: int, **values: object) -> SimpleNamespace:
    return SimpleNamespace(source_id=f"{dataset}.csv", source_row=number, values=values)


def _slot(
    day: str,
    line: str,
    shift: str,
    order: str,
    plan: int,
    actual: int,
    good: int,
    downtime: str = "0",
    runtime: str = "400",
) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    common = dict(
        production_date=day,
        line_id=line,
        shift_id=shift,
        order_id=order,
        product_id=f"P-{order}",
        qty_unit="ea",
    )
    row_number = 2 + int(order.split("-")[-1])
    return (
        _row(
            "production_plan",
            row_number,
            **common,
            planned_qty=plan,
            planned_production_minutes=Decimal("480.000"),
        ),
        _row(
            "production_actual",
            row_number,
            **common,
            actual_qty=actual,
            runtime_minutes=Decimal(runtime).quantize(Decimal("0.001")),
            downtime_minutes=Decimal(downtime).quantize(Decimal("0.001")),
        ),
        _row(
            "quality",
            row_number,
            **common,
            good_qty=good,
            scrap_qty=actual - good,
        ),
    )


def _inventory(
    material: str, day: str, balance: str, buffer: str, unit: str = "kg", row: int = 2
) -> SimpleNamespace:
    return _row(
        "inventory",
        row,
        snapshot_date=day,
        material_id=material,
        qty_unit=unit,
        inventory_qty=Decimal(balance).quantize(Decimal("0.001")),
        safety_stock=Decimal(buffer).quantize(Decimal("0.001")),
    )


def _batch(
    slots: list[tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]] | None = None,
    inventory: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    if slots is None:
        slots = [
            _slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 100, 80, 72, "10.500"),
            _slot("2026-01-02", "LINE-02", "SHIFT-1", "O-2", 300, 300, 294, "20.250"),
        ]
    if inventory is None:
        inventory = [
            _inventory("A", "2025-12-31", "125.500", "150.000", row=2),
            _inventory("B", "2026-01-02", "10", "10", "ea", row=3),
            _inventory("C", "2026-01-01", "0", "0", "m", row=4),
        ]
    return SimpleNamespace(
        identity=SimpleNamespace(
            batch_id="B-1",
            fingerprint="fixture-fingerprint",
            contract_version="0.1-draft",
        ),
        production_plan=tuple(slot[0] for slot in slots),
        production_actual=tuple(slot[1] for slot in slots),
        quality=tuple(slot[2] for slot in slots),
        inventory=tuple(inventory),
    )


def test_normal_metrics_and_lineage() -> None:
    results = calculate_kpis(_batch(), SCOPE)
    assert results["KPI-PA"].value == Fraction(95)
    assert results["KPI-PA"].display_value == "95.00%"
    assert (results["KPI-PA"].numerator, results["KPI-PA"].denominator) == (380, 400)
    assert results["KPI-GY"].value == Fraction(100 * 366, 380)
    assert results["KPI-SR"].value == Fraction(100 * 14, 380)
    assert results["KPI-GY"].value + results["KPI-SR"].value == 100
    assert results["KPI-TD"].value == Decimal("30.750")
    assert results["KPI-TD"].display_value == "30.750 line-minutes"
    assert results["KPI-IR"].value == 1
    assert results["KPI-OL"].value == {"LINE-01": 80, "LINE-02": 300}
    assert results["KPI-PA"].batch_id == "B-1"
    assert results["KPI-PA"].definition_version == "0.1-draft"
    assert len(results["KPI-PA"].source_refs) == 6


def test_documented_yield_and_scrap_example() -> None:
    batch = _batch(
        [
            _slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 100, 100, 90),
            _slot("2026-01-02", "LINE-02", "SHIFT-1", "O-2", 300, 300, 294),
        ]
    )
    assert good_yield(batch, SCOPE).value == Fraction(96)
    assert scrap_rate(batch, SCOPE).value == Fraction(4)


def test_attainment_zero_plan_and_unplanned_output() -> None:
    batch = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 0, 20, 20)])
    assert production_attainment(batch, SCOPE).status == "zero_denominator"
    batch = _batch(
        [
            _slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 100, 80, 80),
            _slot("2026-01-02", "LINE-01", "SHIFT-1", "O-2", 0, 20, 20),
        ]
    )
    assert production_attainment(batch, SCOPE).value == Fraction(100)
    over = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 100, 120, 120)])
    assert production_attainment(over, SCOPE).value == Fraction(120)


def test_zero_output_distinguishes_rates_and_additive_metrics() -> None:
    batch = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 100, 0, 0)])
    assert production_attainment(batch, SCOPE).value == Fraction(0)
    assert good_yield(batch, SCOPE).status == "zero_denominator"
    assert scrap_rate(batch, SCOPE).status == "zero_denominator"
    assert total_downtime(batch, SCOPE).value == Decimal("0.000")
    assert output_by_production_line(batch, SCOPE).value == {"LINE-01": 0}


def test_positive_output_can_have_zero_good_or_zero_scrap() -> None:
    all_scrap = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 10, 10, 0)])
    assert good_yield(all_scrap, SCOPE).value == Fraction(0)
    assert scrap_rate(all_scrap, SCOPE).value == Fraction(100)
    all_good = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 10, 10, 10)])
    assert good_yield(all_good, SCOPE).value == Fraction(100)
    assert scrap_rate(all_good, SCOPE).value == Fraction(0)


def test_percentage_display_uses_half_up_without_changing_exact_value() -> None:
    batch = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 32, 1, 1)])
    result = production_attainment(batch, SCOPE)
    assert result.value == Fraction(25, 8)
    assert result.display_value == "3.13%"


def test_empty_production_scope_is_no_data() -> None:
    results = calculate_kpis(_batch(), KpiScope("2026-02-01", "2026-02-02"))
    for key in ("KPI-PA", "KPI-GY", "KPI-SR", "KPI-TD", "KPI-OL"):
        assert results[key].status == "no_data"
        assert results[key].value is None
    assert results["KPI-IR"].status == "valid"


def test_inclusive_date_and_line_shift_filters() -> None:
    batch = _batch()
    one_day = KpiScope("2026-01-02", "2026-01-02", line_ids=("LINE-02",))
    assert production_attainment(batch, one_day).value == Fraction(100)
    assert output_by_production_line(batch, one_day).value == {"LINE-02": 300}
    none = KpiScope("2026-01-01", "2026-01-02", shift_ids=("SHIFT-2",))
    assert production_attainment(batch, none).status == "no_data"
    assert inventory_risk(batch, none).value == 1


def test_product_filter_and_chart_series_share_the_kpi_population() -> None:
    selected = KpiScope("2026-01-01", "2026-01-02", product_ids=("P-O-1",))
    dashboard = calculate_dashboard_data(_batch(), selected)
    assert dashboard.metrics["KPI-PA"].value == 80
    assert dashboard.metrics["KPI-IR"].value == 1
    assert [
        (point.group, point.planned_qty, point.actual_qty) for point in dashboard.series.daily
    ] == [("2026-01-01", 100, 80)]
    assert [
        (point.group, point.good_qty, point.scrap_qty) for point in dashboard.series.by_line
    ] == [("LINE-01", 72, 8)]
    empty = calculate_dashboard_data(_batch(), KpiScope("2026-01-01", "2026-01-02", product_ids=()))
    assert empty.metrics["KPI-PA"].status == "no_data"
    assert empty.series.daily == ()
    assert empty.metrics["KPI-IR"].value == 1


@pytest.mark.parametrize(
    ("dataset", "field"),
    [
        ("production_plan", "planned_qty"),
        ("production_actual", "actual_qty"),
        ("quality", "good_qty"),
        ("production_actual", "downtime_minutes"),
        ("inventory", "inventory_qty"),
    ],
)
def test_missing_canonical_value_blocks_all_metrics(dataset: str, field: str) -> None:
    batch = deepcopy(_batch())
    getattr(batch, dataset)[0].values.pop(field)
    results = calculate_kpis(batch, SCOPE)
    assert all(result.status == "invalid_data" for result in results.values())


def test_invalid_record_outside_filter_still_blocks_calculation() -> None:
    batch = deepcopy(_batch())
    batch.quality[1].values["scrap_qty"] = 7
    assert (
        production_attainment(batch, KpiScope("2026-01-01", "2026-01-01")).status == "invalid_data"
    )


def test_inventory_as_of_carry_forward_and_partial_coverage() -> None:
    batch = _batch(
        inventory=[
            _inventory("A", "2025-12-31", "125.500", "150.000", row=2),
            _inventory("A", "2026-01-03", "170", "150", row=3),
            _inventory("B", "2026-01-02", "10", "10", "ea", row=4),
            _inventory("C", "2026-01-01", "0", "0", "m", row=5),
            _inventory("D", "2026-01-03", "1", "5", row=6),
        ]
    )
    result = inventory_risk(batch, SCOPE)
    assert result.status == "partial_coverage"
    assert result.value is None
    assert result.coverage == {
        "known_materials": 4,
        "observed_materials": 3,
        "missing_materials": 1,
        "observed_at_risk": 1,
        "line_shift_filters_apply": False,
    }
    assert result.details[0]["carried_forward"] is True
    assert result.details[0]["snapshot_date"] == "2025-12-31"
    assert result.details[3]["status"] == "missing_as_of_snapshot"
    assert len(result.source_refs) == 3


def test_inventory_boundary_zero_and_empty_material_selection() -> None:
    safe = _batch(inventory=[_inventory("B", "2026-01-02", "10", "10", "ea")])
    assert inventory_risk(safe, SCOPE).value == 0
    assert (
        inventory_risk(safe, KpiScope("2026-01-01", "2026-01-02", material_ids=())).status
        == "no_data"
    )


def test_output_by_line_sums_slots_without_deduplicating_order() -> None:
    batch = _batch(
        [
            _slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 100, 80, 80),
            _slot("2026-01-01", "LINE-01", "SHIFT-2", "O-1", 120, 120, 120),
            _slot("2026-01-02", "LINE-02", "SHIFT-1", "O-2", 300, 300, 300),
        ]
    )
    result = output_by_production_line(batch, SCOPE)
    assert result.value == {"LINE-01": 200, "LINE-02": 300}
    assert sum(result.value.values()) == 500


@pytest.mark.parametrize("function", [completed_orders, schedule_adherence])
def test_order_lifecycle_metrics_remain_unsupported(function: object) -> None:
    assert function(_batch(), SCOPE).status == "unsupported_schema"
    zero = _batch([_slot("2026-01-01", "LINE-01", "SHIFT-1", "O-1", 0, 0, 0)])
    assert function(zero, SCOPE).value is None
    assert function(zero, SCOPE).status == "unsupported_schema"
    assert function(_batch(), KpiScope("2026-02-01", "2026-02-02")).status == ("unsupported_schema")


def test_unknown_contract_version_is_explicit() -> None:
    batch = _batch()
    batch.identity.contract_version = "future"
    assert all(
        result.status == "unsupported_schema" for result in calculate_kpis(batch, SCOPE).values()
    )


def test_scope_rejects_ambiguous_dates() -> None:
    with pytest.raises(ValueError):
        KpiScope("2026-01-02", "2026-01-01")
    with pytest.raises(ValueError):
        KpiScope("2026-1-1", "2026-01-02")
