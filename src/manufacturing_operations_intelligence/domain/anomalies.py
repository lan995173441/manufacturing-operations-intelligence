"""Configurable, deterministic operational exception rules over validated KPI evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from types import MappingProxyType
from typing import Any, Literal

from manufacturing_operations_intelligence.domain.analytics import (
    KpiScope,
    SourceReference,
    calculate_anomaly_inputs,
)

RULE_VERSION = "0.1-draft"
LOW_ATTAINMENT = "LOW_ATTAINMENT"
HIGH_SCRAP_RATE = "HIGH_SCRAP_RATE"
HIGH_DOWNTIME = "HIGH_DOWNTIME"
LOW_INVENTORY = "LOW_INVENTORY"
HIGH_PRODUCTION_VARIANCE = "HIGH_PRODUCTION_VARIANCE"
RULE_TYPES = frozenset(
    {
        LOW_ATTAINMENT,
        HIGH_SCRAP_RATE,
        HIGH_DOWNTIME,
        LOW_INVENTORY,
        HIGH_PRODUCTION_VARIANCE,
    }
)
Severity = Literal["INFO", "WARNING", "CRITICAL"]
ResultStatus = Literal["valid", "no_data", "partial_coverage", "invalid_data", "unsupported_schema"]


@dataclass(frozen=True)
class RuleConfig:
    downtime_above_minutes: Decimal
    attainment_below_percent: Decimal = Decimal("90")
    scrap_above_percent: Decimal = Decimal("5")
    variance_above_percent: Decimal = Decimal("10")
    enabled_rules: frozenset[str] = RULE_TYPES
    severities: Mapping[str, Severity] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "downtime_above_minutes",
            "attainment_below_percent",
            "scrap_above_percent",
            "variance_above_percent",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError(f"{name} must be a finite nonnegative Decimal.")
        if not isinstance(self.enabled_rules, frozenset) or not self.enabled_rules <= RULE_TYPES:
            raise ValueError("enabled_rules must be a frozenset of known anomaly types.")
        if set(self.severities) - RULE_TYPES:
            raise ValueError("Unknown anomaly type in severity configuration.")
        if any(value not in {"INFO", "WARNING", "CRITICAL"} for value in self.severities.values()):
            raise ValueError("Severity must be INFO, WARNING or CRITICAL.")
        object.__setattr__(
            self,
            "severities",
            MappingProxyType({rule: self.severities.get(rule, "WARNING") for rule in RULE_TYPES}),
        )


@dataclass(frozen=True)
class AnomalyEntity:
    kind: Literal["production_slot", "material"]
    key: str
    order_id: str | None = None
    product_id: str | None = None


@dataclass(frozen=True)
class Anomaly:
    type: str
    severity: Severity
    entity: AnomalyEntity
    observed_value: Fraction | Decimal
    threshold: Fraction | Decimal
    unit: str
    date_start: str
    date_end: str
    explanation: str
    comparator: Literal["<", ">"]
    source_refs: tuple[SourceReference, ...]
    rule_version: str = RULE_VERSION


@dataclass(frozen=True)
class SkippedRule:
    type: str
    entity: AnomalyEntity
    date_start: str
    date_end: str
    reason: str


@dataclass(frozen=True)
class DetectionResult:
    status: ResultStatus
    anomalies: tuple[Anomaly, ...]
    skipped: tuple[SkippedRule, ...]
    evaluated_count: int
    reason: str | None
    scope: KpiScope
    batch_id: str | None
    rule_version: str = RULE_VERSION

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def _percent_text(value: Fraction | Decimal) -> str:
    fraction = Fraction(value)
    with localcontext() as context:
        context.prec = 40
        rounded = (Decimal(fraction.numerator) / Decimal(fraction.denominator)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    return f"{rounded}%"


def detect_anomalies(batch: Any | None, scope: KpiScope, config: RuleConfig) -> DetectionResult:
    """Evaluate selected production slots and latest eligible material snapshots."""
    inputs = calculate_anomaly_inputs(batch, scope)
    if inputs.status is not None:
        identity = getattr(batch, "identity", None)
        return DetectionResult(
            inputs.status,
            (),
            (),
            0,
            inputs.reason,
            scope,
            identity.batch_id if identity else None,
        )
    anomalies: list[Anomaly] = []
    skipped: list[SkippedRule] = []
    evaluated = 0

    def compare(
        rule: str,
        entity: AnomalyEntity,
        observed: Fraction | Decimal,
        threshold: Fraction | Decimal,
        unit: str,
        start: str,
        end: str,
        refs: tuple[SourceReference, ...],
        explanation: str,
        comparator: Literal["<", ">"],
    ) -> None:
        nonlocal evaluated
        if rule not in config.enabled_rules:
            return
        evaluated += 1
        triggered = observed < threshold if comparator == "<" else observed > threshold
        if triggered:
            anomalies.append(
                Anomaly(
                    rule,
                    config.severities[rule],
                    entity,
                    observed,
                    threshold,
                    unit,
                    start,
                    end,
                    explanation,
                    comparator,
                    refs,
                )
            )

    def skip(rule: str, entity: AnomalyEntity, day: str, reason: str) -> None:
        if rule in config.enabled_rules:
            skipped.append(SkippedRule(rule, entity, day, day, reason))

    for slot in inputs.slots:
        day = slot.production_date
        entity = AnomalyEntity(
            "production_slot",
            f"{day}/{slot.line_id}/{slot.shift_id}",
            slot.order_id,
            slot.product_id,
        )
        attainment = slot.attainment
        if attainment.status == "valid":
            threshold = Fraction(config.attainment_below_percent)
            compare(
                LOW_ATTAINMENT,
                entity,
                attainment.value,
                threshold,
                "%",
                day,
                day,
                attainment.source_refs,
                f"Production attainment {_percent_text(attainment.value)} is below "
                f"the configured {_percent_text(threshold)} for {entity.key}.",
                "<",
            )
            # The user-approved variance is absolute slot output deviation from plan.
            variance = Fraction(
                100 * abs(attainment.numerator - attainment.denominator),
                attainment.denominator,
            )
            variance_threshold = Fraction(config.variance_above_percent)
            compare(
                HIGH_PRODUCTION_VARIANCE,
                entity,
                variance,
                variance_threshold,
                "%",
                day,
                day,
                attainment.source_refs,
                f"Absolute production variance {_percent_text(variance)} exceeds "
                f"the configured {_percent_text(variance_threshold)} for {entity.key}.",
                ">",
            )
        else:
            skip(LOW_ATTAINMENT, entity, day, attainment.reason or attainment.status)
            skip(
                HIGH_PRODUCTION_VARIANCE,
                entity,
                day,
                "Production variance is undefined when planned quantity is zero.",
            )
        scrap = slot.scrap_rate
        if scrap.status == "valid":
            threshold = Fraction(config.scrap_above_percent)
            compare(
                HIGH_SCRAP_RATE,
                entity,
                scrap.value,
                threshold,
                "%",
                day,
                day,
                scrap.source_refs,
                f"Final scrap rate {_percent_text(scrap.value)} exceeds "
                f"the configured {_percent_text(threshold)} for {entity.key}.",
                ">",
            )
        else:
            skip(HIGH_SCRAP_RATE, entity, day, scrap.reason or scrap.status)
        downtime = slot.downtime
        compare(
            HIGH_DOWNTIME,
            entity,
            downtime.value,
            config.downtime_above_minutes,
            "line-minutes",
            day,
            day,
            downtime.source_refs,
            f"Recorded downtime {downtime.value:.3f} line-minutes exceeds "
            f"the configured {config.downtime_above_minutes:.3f} for {entity.key}.",
            ">",
        )

    inventory = inputs.inventory
    if inventory is not None:
        ref_by_material = {
            item["material_id"]: ref
            for item, ref in zip(
                (item for item in inventory.details if item["status"] == "observed"),
                inventory.source_refs,
                strict=True,
            )
        }
        for item in inventory.details:
            entity = AnomalyEntity("material", item["material_id"])
            if item["status"] != "observed":
                skip(
                    LOW_INVENTORY,
                    entity,
                    scope.end_date,
                    "No eligible inventory snapshot exists by the as-of date.",
                )
                continue
            observed = item["inventory_qty"]
            threshold = item["safety_stock"]
            day = item["snapshot_date"]
            compare(
                LOW_INVENTORY,
                entity,
                observed,
                threshold,
                item["qty_unit"],
                day,
                scope.end_date,
                (ref_by_material[item["material_id"]],),
                f"Material {item['material_id']} balance {observed:.3f} "
                f"{item['qty_unit']} observed on {day} is below its source-supplied "
                f"safety stock {threshold:.3f} {item['qty_unit']} as of {scope.end_date}.",
                "<",
            )
    observed_inventory = bool(
        inventory and any(item["status"] == "observed" for item in inventory.details)
    )
    if inventory and inventory.status == "partial_coverage":
        status: ResultStatus = "partial_coverage"
    elif inputs.slots or observed_inventory:
        status = "valid"
    else:
        status = "no_data"
    reason = (
        "Some known materials lack an eligible as-of inventory snapshot."
        if status == "partial_coverage"
        else None
    )
    batch_id = inventory.batch_id if inventory is not None else None
    return DetectionResult(
        status,
        tuple(anomalies),
        tuple(skipped),
        evaluated,
        reason,
        scope,
        batch_id,
    )
