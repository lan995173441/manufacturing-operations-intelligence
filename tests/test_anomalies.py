"""Independent boundary fixtures for the five deterministic anomaly rules."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

import pytest

from manufacturing_operations_intelligence.domain.analytics import KpiScope
from manufacturing_operations_intelligence.domain.anomalies import (
    HIGH_DOWNTIME,
    HIGH_PRODUCTION_VARIANCE,
    HIGH_SCRAP_RATE,
    LOW_ATTAINMENT,
    LOW_INVENTORY,
    RuleConfig,
    detect_anomalies,
)

SCOPE = KpiScope("2026-01-01", "2026-01-02")


def _batch(
    *,
    plan: int = 100,
    actual: int = 100,
    scrap: int = 0,
    downtime: str = "0",
    balance: str = "20",
    safety: str = "10",
    inventory_date: str = "2026-01-02",
) -> SimpleNamespace:
    common = {
        "production_date": "2026-01-01",
        "line_id": "LINE-01",
        "shift_id": "SHIFT-1",
        "order_id": "O-1",
        "product_id": "P-1",
        "qty_unit": "ea",
    }

    def row(dataset: str, number: int, values: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(source_id=f"{dataset}.csv", source_row=number, values=values)

    return SimpleNamespace(
        identity=SimpleNamespace(
            batch_id="B-1", fingerprint="fixture", contract_version="0.1-draft"
        ),
        production_plan=(
            row(
                "production_plan",
                2,
                {
                    **common,
                    "planned_qty": plan,
                    "planned_production_minutes": Decimal("480.000"),
                },
            ),
        ),
        production_actual=(
            row(
                "production_actual",
                2,
                {
                    **common,
                    "actual_qty": actual,
                    "runtime_minutes": Decimal("400.000"),
                    "downtime_minutes": Decimal(downtime).quantize(Decimal("0.001")),
                },
            ),
        ),
        quality=(
            row(
                "quality",
                2,
                {
                    **common,
                    "good_qty": actual - scrap,
                    "scrap_qty": scrap,
                },
            ),
        ),
        inventory=(
            row(
                "inventory",
                2,
                {
                    "snapshot_date": inventory_date,
                    "material_id": "MAT-1",
                    "qty_unit": "ea",
                    "inventory_qty": Decimal(balance).quantize(Decimal("0.001")),
                    "safety_stock": Decimal(safety).quantize(Decimal("0.001")),
                },
            ),
        ),
    )


def _config(rule: str | None = None, **values: object) -> RuleConfig:
    return RuleConfig(
        downtime_above_minutes=Decimal("30"),
        enabled_rules=frozenset({rule})
        if rule
        else frozenset(
            {
                LOW_ATTAINMENT,
                HIGH_SCRAP_RATE,
                HIGH_DOWNTIME,
                LOW_INVENTORY,
                HIGH_PRODUCTION_VARIANCE,
            }
        ),
        **values,
    )


@pytest.mark.parametrize(
    ("rule", "kwargs", "observed", "threshold"),
    [
        (LOW_ATTAINMENT, {"actual": 89}, Fraction(89), Fraction(90)),
        (HIGH_SCRAP_RATE, {"scrap": 6}, Fraction(6), Fraction(5)),
        (HIGH_DOWNTIME, {"downtime": "31"}, Decimal("31.000"), Decimal("30")),
        (LOW_INVENTORY, {"balance": "9"}, Decimal("9.000"), Decimal("10.000")),
        (HIGH_PRODUCTION_VARIANCE, {"actual": 111}, Fraction(11), Fraction(10)),
    ],
)
def test_each_rule_triggers_with_exact_evidence(
    rule: str, kwargs: dict[str, object], observed: object, threshold: object
) -> None:
    result = detect_anomalies(_batch(**kwargs), SCOPE, _config(rule))
    assert result.status == "valid"
    assert result.anomaly_count == 1
    anomaly = result.anomalies[0]
    assert anomaly.type == rule
    assert anomaly.observed_value == observed
    assert anomaly.threshold == threshold
    assert anomaly.date_start <= anomaly.date_end
    assert anomaly.explanation
    assert len(anomaly.source_refs) >= 1
    assert anomaly.entity.key
    assert anomaly.severity == "WARNING"


def test_no_rule_triggers_for_normal_operations() -> None:
    result = detect_anomalies(
        _batch(actual=100, scrap=4, downtime="10", balance="12"),
        SCOPE,
        _config(),
    )
    assert result.status == "valid"
    assert result.anomalies == ()
    assert result.evaluated_count == 5
    assert result.skipped_count == 0


@pytest.mark.parametrize(
    ("rule", "kwargs"),
    [
        (LOW_ATTAINMENT, {"actual": 90}),
        (HIGH_SCRAP_RATE, {"scrap": 5}),
        (HIGH_DOWNTIME, {"downtime": "30"}),
        (LOW_INVENTORY, {"balance": "10"}),
        (HIGH_PRODUCTION_VARIANCE, {"actual": 110}),
    ],
)
def test_exact_threshold_does_not_trigger(rule: str, kwargs: dict[str, object]) -> None:
    result = detect_anomalies(_batch(**kwargs), SCOPE, _config(rule))
    assert result.anomalies == ()
    assert result.evaluated_count == 1


def test_multiple_simultaneous_anomalies_are_retained() -> None:
    result = detect_anomalies(
        _batch(actual=80, scrap=8, downtime="40", balance="5"),
        SCOPE,
        _config(),
    )
    assert {anomaly.type for anomaly in result.anomalies} == {
        LOW_ATTAINMENT,
        HIGH_SCRAP_RATE,
        HIGH_DOWNTIME,
        LOW_INVENTORY,
        HIGH_PRODUCTION_VARIANCE,
    }
    assert result.anomaly_count == 5
    assert result.evaluated_count == 5
    assert result.skipped_count == 0
    assert all(anomaly.rule_version == "0.1-draft" for anomaly in result.anomalies)


def test_zero_plan_and_zero_output_skip_undefined_ratios() -> None:
    result = detect_anomalies(_batch(plan=0, actual=0), SCOPE, _config())
    assert result.anomalies == ()
    assert {item.type for item in result.skipped} == {
        LOW_ATTAINMENT,
        HIGH_PRODUCTION_VARIANCE,
        HIGH_SCRAP_RATE,
    }
    assert result.evaluated_count == 2


def test_missing_as_of_inventory_is_skipped_and_partial() -> None:
    result = detect_anomalies(_batch(inventory_date="2026-01-03", balance="1"), SCOPE, _config())
    assert result.status == "partial_coverage"
    assert result.reason
    assert any(item.type == LOW_INVENTORY for item in result.skipped)
    assert all(item.type != LOW_INVENTORY for item in result.anomalies)


def test_partial_inventory_still_reports_observed_low_stock() -> None:
    batch = _batch(balance="5")
    batch.inventory += (
        SimpleNamespace(
            source_id="inventory.csv",
            source_row=3,
            values={
                "snapshot_date": "2026-01-03",
                "material_id": "MAT-2",
                "qty_unit": "ea",
                "inventory_qty": Decimal("1.000"),
                "safety_stock": Decimal("10.000"),
            },
        ),
    )
    result = detect_anomalies(batch, SCOPE, _config(LOW_INVENTORY))
    assert result.status == "partial_coverage"
    assert [item.entity.key for item in result.anomalies] == ["MAT-1"]
    assert [item.entity.key for item in result.skipped] == ["MAT-2"]
    assert result.evaluated_count == 1


def test_invalid_batch_blocks_all_rules_even_outside_selected_range() -> None:
    batch = deepcopy(_batch())
    batch.quality[0].values["scrap_qty"] = 1
    result = detect_anomalies(batch, KpiScope("2026-02-01", "2026-02-02"), _config())
    assert result.status == "invalid_data"
    assert result.anomalies == ()
    assert result.evaluated_count == 0


def test_threshold_and_severity_configuration() -> None:
    config = _config(
        attainment_below_percent=Decimal("101"),
        severities={LOW_ATTAINMENT: "CRITICAL", LOW_INVENTORY: "INFO"},
    )
    result = detect_anomalies(_batch(balance="5"), SCOPE, config)
    severity = {item.type: item.severity for item in result.anomalies}
    assert severity[LOW_ATTAINMENT] == "CRITICAL"
    assert severity[LOW_INVENTORY] == "INFO"
    assert detect_anomalies(_batch(balance="5"), SCOPE, config) == result


def test_all_rules_can_be_disabled_without_claiming_missing_data() -> None:
    result = detect_anomalies(
        _batch(actual=50, balance="5"),
        SCOPE,
        RuleConfig(Decimal("30"), enabled_rules=frozenset()),
    )
    assert result.status == "valid"
    assert result.evaluated_count == 0
    assert result.anomalies == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"downtime_above_minutes": Decimal("-1")},
        {"downtime_above_minutes": Decimal("NaN")},
        {"downtime_above_minutes": 10},
        {"downtime_above_minutes": Decimal("30"), "enabled_rules": frozenset({"UNKNOWN"})},
        {"downtime_above_minutes": Decimal("30"), "severities": {LOW_INVENTORY: "ERROR"}},
    ],
)
def test_invalid_configuration_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        RuleConfig(**kwargs)
