"""Deterministic KPI calculations over one canonical batch; no UI or storage dependency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from typing import Any, Literal

from manufacturing_operations_intelligence.domain.validation import (
    PRODUCTION_KEY,
    validate_normalized_records,
)

DEFINITION_VERSION = "0.1-draft"
CONTRACT_VERSION = "0.1-draft"
Status = Literal[
    "valid",
    "no_data",
    "zero_denominator",
    "partial_coverage",
    "unsupported_schema",
    "invalid_data",
]
KPI_UNITS = {
    "KPI-PA": "%",
    "KPI-GY": "%",
    "KPI-SR": "%",
    "KPI-TD": "line-minutes",
    "KPI-CO": "orders",
    "KPI-SA": "%",
    "KPI-IR": "materials",
    "KPI-OL": "ea",
}
UNSUPPORTED = {
    "KPI-CO": "Verified order completion events and a complete order census are absent.",
    "KPI-SA": "Committed due times, completion evidence, cutoff and order census are absent.",
}


@dataclass(frozen=True)
class KpiScope:
    start_date: str
    end_date: str
    line_ids: tuple[str, ...] | None = None
    shift_ids: tuple[str, ...] | None = None
    material_ids: tuple[str, ...] | None = None
    product_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        try:
            start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
        except (TypeError, ValueError) as exc:
            raise ValueError("KPI scope requires ISO YYYY-MM-DD dates.") from exc
        if start.isoformat() != self.start_date or end.isoformat() != self.end_date:
            raise ValueError("KPI scope requires ISO YYYY-MM-DD dates.")
        if start > end:
            raise ValueError("KPI scope start_date must not exceed end_date.")


@dataclass(frozen=True)
class SourceReference:
    dataset: str
    source_id: str
    source_row: int


@dataclass(frozen=True)
class KpiResult:
    kpi_id: str
    status: Status
    value: Fraction | Decimal | int | dict[str, int] | None
    display_value: str | None
    unit: str
    reason: str | None
    scope: KpiScope
    batch_id: str | None
    fingerprint: str | None
    contract_version: str | None
    definition_version: str = DEFINITION_VERSION
    numerator: int | None = None
    denominator: int | None = None
    coverage: dict[str, Any] = field(default_factory=dict)
    source_refs: tuple[SourceReference, ...] = ()
    details: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class SlotKpis:
    production_date: str
    line_id: str
    shift_id: str
    order_id: str
    product_id: str
    attainment: KpiResult
    scrap_rate: KpiResult
    downtime: KpiResult


@dataclass(frozen=True)
class AnomalyInputs:
    status: Status | None
    reason: str | None
    slots: tuple[SlotKpis, ...]
    inventory: KpiResult | None


@dataclass(frozen=True)
class ProductionSummary:
    group: str
    planned_qty: int
    actual_qty: int
    good_qty: int
    scrap_qty: int
    downtime_minutes: Decimal


@dataclass(frozen=True)
class DashboardSeries:
    daily: tuple[ProductionSummary, ...] = ()
    by_line: tuple[ProductionSummary, ...] = ()


@dataclass(frozen=True)
class DashboardData:
    metrics: dict[str, KpiResult]
    series: DashboardSeries


@dataclass(frozen=True)
class _Prepared:
    batch: Any | None
    scope: KpiScope
    status: Status | None
    reason: str | None
    slots: tuple[tuple[Any, Any, Any], ...] = ()
    records: dict[str, tuple[Any, ...]] = field(default_factory=dict)


def _key(row: Any) -> tuple[str, str, str]:
    return tuple(row.values[name] for name in PRODUCTION_KEY)


def _prepare(batch: Any | None, scope: KpiScope) -> _Prepared:
    if batch is None:
        return _Prepared(batch, scope, "no_data", "No accepted batch is available.")
    if batch.identity.contract_version != CONTRACT_VERSION:
        return _Prepared(batch, scope, "unsupported_schema", "Unknown data contract version.")
    records = {
        name: tuple(getattr(batch, name))
        for name in ("production_plan", "production_actual", "quality", "inventory")
    }
    errors = tuple(
        issue for issue in validate_normalized_records(records) if issue.severity == "ERROR"
    )
    if errors:
        first = errors[0]
        reason = (
            f"Accepted batch failed canonical validation: {first.code} "
            f"({first.dataset}, row {first.row})."
        )
        return _Prepared(batch, scope, "invalid_data", reason, records=records)
    actual = {_key(row): row for row in records["production_actual"]}
    quality = {_key(row): row for row in records["quality"]}
    slots = []
    for plan in records["production_plan"]:
        day, line, shift = _key(plan)
        if not scope.start_date <= day <= scope.end_date:
            continue
        if scope.line_ids is not None and line not in scope.line_ids:
            continue
        if scope.shift_ids is not None and shift not in scope.shift_ids:
            continue
        if scope.product_ids is not None and plan.values["product_id"] not in scope.product_ids:
            continue
        slots.append((plan, actual[_key(plan)], quality[_key(plan)]))
    return _Prepared(batch, scope, None, None, tuple(slots), records)


def _refs(rows: tuple[tuple[str, Any], ...]) -> tuple[SourceReference, ...]:
    return tuple(SourceReference(name, row.source_id, row.source_row) for name, row in rows)


def _production_refs(slots: tuple[tuple[Any, Any, Any], ...]) -> tuple[SourceReference, ...]:
    return _refs(
        tuple(
            (name, row)
            for slot in slots
            for name, row in zip(
                ("production_plan", "production_actual", "quality"), slot, strict=True
            )
        )
    )


def _result(
    prepared: _Prepared,
    kpi_id: str,
    status: Status,
    *,
    value: Fraction | Decimal | int | dict[str, int] | None = None,
    display_value: str | None = None,
    reason: str | None = None,
    numerator: int | None = None,
    denominator: int | None = None,
    coverage: dict[str, Any] | None = None,
    source_refs: tuple[SourceReference, ...] = (),
    details: tuple[dict[str, Any], ...] = (),
) -> KpiResult:
    identity = prepared.batch.identity if prepared.batch is not None else None
    return KpiResult(
        kpi_id,
        status,
        value,
        display_value,
        KPI_UNITS[kpi_id],
        reason,
        prepared.scope,
        identity.batch_id if identity else None,
        identity.fingerprint if identity else None,
        identity.contract_version if identity else None,
        numerator=numerator,
        denominator=denominator,
        coverage=coverage or {},
        source_refs=source_refs,
        details=details,
    )


def _unavailable(prepared: _Prepared, kpi_id: str) -> KpiResult | None:
    if prepared.status:
        return _result(prepared, kpi_id, prepared.status, reason=prepared.reason)
    if kpi_id in UNSUPPORTED:
        return _result(prepared, kpi_id, "unsupported_schema", reason=UNSUPPORTED[kpi_id])
    if kpi_id != "KPI-IR" and not prepared.slots:
        return _result(
            prepared,
            kpi_id,
            "no_data",
            reason="No selected production slots.",
            coverage={"observed_slots": 0},
        )
    return None


def _percent(prepared: _Prepared, kpi_id: str, numerator: int, denominator: int) -> KpiResult:
    evidence = {"observed_slots": len(prepared.slots)}
    refs = _production_refs(prepared.slots)
    if denominator == 0:
        return _result(
            prepared,
            kpi_id,
            "zero_denominator",
            reason="Summed denominator is zero.",
            numerator=numerator,
            denominator=denominator,
            coverage=evidence,
            source_refs=refs,
        )
    exact = Fraction(100 * numerator, denominator)
    with localcontext() as context:
        context.prec = 40
        displayed = (Decimal(100 * numerator) / Decimal(denominator)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    return _result(
        prepared,
        kpi_id,
        "valid",
        value=exact,
        display_value=f"{displayed}%",
        numerator=numerator,
        denominator=denominator,
        coverage=evidence,
        source_refs=refs,
    )


def _inventory_risk(prepared: _Prepared) -> KpiResult:
    rows = prepared.records["inventory"]
    universe = sorted({row.values["material_id"] for row in rows})
    if prepared.scope.material_ids is not None:
        universe = [material for material in universe if material in prepared.scope.material_ids]
    if not universe:
        return _result(
            prepared,
            "KPI-IR",
            "no_data",
            reason="No known materials in scope.",
            coverage={"known_materials": 0},
        )
    latest: dict[str, Any] = {}
    for row in rows:
        material = row.values["material_id"]
        day = row.values["snapshot_date"]
        if material not in universe or day > prepared.scope.end_date:
            continue
        previous = latest.get(material)
        if previous is None or day > previous.values["snapshot_date"]:
            latest[material] = row
    details = []
    for material in universe:
        row = latest.get(material)
        if row is None:
            details.append({"material_id": material, "status": "missing_as_of_snapshot"})
            continue
        value = row.values
        details.append(
            {
                "material_id": material,
                "status": "observed",
                "snapshot_date": value["snapshot_date"],
                "carried_forward": value["snapshot_date"] < prepared.scope.start_date,
                "inventory_qty": value["inventory_qty"],
                "safety_stock": value["safety_stock"],
                "qty_unit": value["qty_unit"],
                "below_safety_stock": value["inventory_qty"] < value["safety_stock"],
            }
        )
    at_risk = sum(item.get("below_safety_stock", False) for item in details)
    coverage = {
        "known_materials": len(universe),
        "observed_materials": len(latest),
        "missing_materials": len(universe) - len(latest),
        "observed_at_risk": at_risk,
        "line_shift_filters_apply": False,
    }
    refs = _refs(
        tuple(("inventory", latest[material]) for material in universe if material in latest)
    )
    if len(latest) != len(universe):
        return _result(
            prepared,
            "KPI-IR",
            "partial_coverage",
            reason="Some known materials lack an as-of snapshot.",
            coverage=coverage,
            source_refs=refs,
            details=tuple(details),
        )
    return _result(
        prepared,
        "KPI-IR",
        "valid",
        value=at_risk,
        display_value=f"{at_risk} materials",
        coverage=coverage,
        source_refs=refs,
        details=tuple(details),
    )


def _calculate(prepared: _Prepared, kpi_id: str) -> KpiResult:
    unavailable = _unavailable(prepared, kpi_id)
    if unavailable is not None:
        return unavailable
    slots = prepared.slots
    if kpi_id == "KPI-PA":
        return _percent(
            prepared,
            kpi_id,
            sum(a.values["actual_qty"] for _, a, _ in slots),
            sum(p.values["planned_qty"] for p, _, _ in slots),
        )
    if kpi_id == "KPI-GY":
        return _percent(
            prepared,
            kpi_id,
            sum(q.values["good_qty"] for _, _, q in slots),
            sum(a.values["actual_qty"] for _, a, _ in slots),
        )
    if kpi_id == "KPI-SR":
        return _percent(
            prepared,
            kpi_id,
            sum(q.values["scrap_qty"] for _, _, q in slots),
            sum(a.values["actual_qty"] for _, a, _ in slots),
        )
    if kpi_id == "KPI-TD":
        value = sum((a.values["downtime_minutes"] for _, a, _ in slots), Decimal(0))
        return _result(
            prepared,
            kpi_id,
            "valid",
            value=value,
            display_value=f"{value.quantize(Decimal('0.001'))} line-minutes",
            coverage={"observed_slots": len(slots)},
            source_refs=_production_refs(slots),
        )
    if kpi_id == "KPI-OL":
        output: dict[str, int] = {}
        for _, actual, _ in slots:
            line = actual.values["line_id"]
            output[line] = output.get(line, 0) + actual.values["actual_qty"]
        return _result(
            prepared,
            kpi_id,
            "valid",
            value=dict(sorted(output.items())),
            display_value="; ".join(
                f"{line}: {count} ea" for line, count in sorted(output.items())
            ),
            coverage={"observed_slots": len(slots), "observed_lines": len(output)},
            source_refs=_production_refs(slots),
        )
    if kpi_id == "KPI-IR":
        return _inventory_risk(prepared)
    raise ValueError(f"Unknown KPI: {kpi_id}")


def calculate_kpis(batch: Any | None, scope: KpiScope) -> dict[str, KpiResult]:
    """Calculate all eight KPIs from one coherent, fully checked batch."""
    prepared = _prepare(batch, scope)
    return {kpi_id: _calculate(prepared, kpi_id) for kpi_id in KPI_UNITS}


def _summaries(prepared: _Prepared, group_field: str) -> tuple[ProductionSummary, ...]:
    if prepared.status is not None:
        return ()
    grouped: dict[str, dict[str, int | Decimal]] = {}
    for plan, actual, quality in prepared.slots:
        group = plan.values[group_field]
        values = grouped.setdefault(
            group,
            {
                "planned_qty": 0,
                "actual_qty": 0,
                "good_qty": 0,
                "scrap_qty": 0,
                "downtime_minutes": Decimal(0),
            },
        )
        values["planned_qty"] += plan.values["planned_qty"]
        values["actual_qty"] += actual.values["actual_qty"]
        values["good_qty"] += quality.values["good_qty"]
        values["scrap_qty"] += quality.values["scrap_qty"]
        values["downtime_minutes"] += actual.values["downtime_minutes"]
    return tuple(ProductionSummary(group, **values) for group, values in sorted(grouped.items()))


def calculate_dashboard_data(batch: Any | None, scope: KpiScope) -> DashboardData:
    """Return KPI values and chart series from one validated population."""
    prepared = _prepare(batch, scope)
    return DashboardData(
        {kpi_id: _calculate(prepared, kpi_id) for kpi_id in KPI_UNITS},
        DashboardSeries(
            daily=_summaries(prepared, "production_date"),
            by_line=_summaries(prepared, "line_id"),
        ),
    )


def calculate_anomaly_inputs(batch: Any | None, scope: KpiScope) -> AnomalyInputs:
    """Prepare reusable slot KPI evidence and one as-of inventory result."""
    prepared = _prepare(batch, scope)
    if prepared.status is not None:
        return AnomalyInputs(prepared.status, prepared.reason, (), None)
    slots = []
    for rows in prepared.slots:
        plan = rows[0]
        values = plan.values
        slot_scope = KpiScope(
            values["production_date"],
            values["production_date"],
            line_ids=(values["line_id"],),
            shift_ids=(values["shift_id"],),
        )
        slot_prepared = _Prepared(batch, slot_scope, None, None, (rows,), prepared.records)
        slots.append(
            SlotKpis(
                values["production_date"],
                values["line_id"],
                values["shift_id"],
                values["order_id"],
                values["product_id"],
                _calculate(slot_prepared, "KPI-PA"),
                _calculate(slot_prepared, "KPI-SR"),
                _calculate(slot_prepared, "KPI-TD"),
            )
        )
    return AnomalyInputs(None, None, tuple(slots), _calculate(prepared, "KPI-IR"))


def _single(batch: Any | None, scope: KpiScope, kpi_id: str) -> KpiResult:
    return _calculate(_prepare(batch, scope), kpi_id)


def production_attainment(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-PA")


def good_yield(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-GY")


def scrap_rate(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-SR")


def total_downtime(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-TD")


def completed_orders(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-CO")


def schedule_adherence(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-SA")


def inventory_risk(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-IR")


def output_by_production_line(batch: Any | None, scope: KpiScope) -> KpiResult:
    return _single(batch, scope, "KPI-OL")
