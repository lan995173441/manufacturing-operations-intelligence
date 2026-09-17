"""Deterministic synthetic inputs for demos and automated tests.

Scenario controls in this module describe generated fixtures. They are not
application anomaly thresholds or authoritative manufacturing rules.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

DEFAULT_SEED = 2606
DEFAULT_START_DATE = date(2025, 1, 1)
DEFAULT_DAYS = 90

LINE_IDS = ("LINE-01", "LINE-02", "LINE-03")
SHIFT_IDS = ("DAY", "NIGHT")
PRODUCT_IDS = tuple(f"PRD-{number:03d}" for number in range(1, 21))
MATERIAL_IDS = tuple(f"MAT-{number:03d}" for number in range(1, 41))

PRODUCTION_COMMON_COLUMNS = (
    "production_date",
    "line_id",
    "shift_id",
    "order_id",
    "product_id",
    "qty_unit",
)
PRODUCTION_PLAN_COLUMNS = (*PRODUCTION_COMMON_COLUMNS, "planned_qty", "planned_production_minutes")
PRODUCTION_ACTUAL_COLUMNS = (
    *PRODUCTION_COMMON_COLUMNS,
    "actual_qty",
    "runtime_minutes",
    "downtime_minutes",
)
QUALITY_COLUMNS = (*PRODUCTION_COMMON_COLUMNS, "good_qty", "scrap_qty")
INVENTORY_COLUMNS = (
    "snapshot_date",
    "material_id",
    "qty_unit",
    "inventory_qty",
    "safety_stock",
)

_THREE_PLACES = Decimal("0.001")


@dataclass(frozen=True)
class ScenarioManifest:
    """Declared locations of controlled fixture scenarios."""

    underperformance_line_id: str
    underperformance_dates: tuple[date, ...]
    downtime_spike_line_id: str
    downtime_spike_dates: tuple[date, ...]
    scrap_increase_line_id: str
    scrap_increase_dates: tuple[date, ...]
    low_inventory_material_ids: tuple[str, ...]
    low_inventory_dates: tuple[date, ...]
    incomplete_order_ids: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticDataBundle:
    """The four canonical datasets plus non-canonical fixture metadata."""

    production_plan: pd.DataFrame
    production_actual: pd.DataFrame
    quality: pd.DataFrame
    inventory: pd.DataFrame
    scenarios: ScenarioManifest
    seed: int
    start_date: date
    days: int

    def datasets(self) -> dict[str, pd.DataFrame]:
        """Return canonical datasets keyed by their contract names."""
        return {
            "production_plan": self.production_plan,
            "production_actual": self.production_actual,
            "quality": self.quality,
            "inventory": self.inventory,
        }


def _scenario_manifest(start_date: date) -> ScenarioManifest:
    incomplete_offsets_and_slots = (
        (82, 0, 1),
        (84, 2, 0),
        (86, 1, 1),
        (88, 0, 0),
    )
    incomplete_order_ids = tuple(
        _order_id(day_offset, line_index, shift_index)
        for day_offset, line_index, shift_index in incomplete_offsets_and_slots
    )
    return ScenarioManifest(
        underperformance_line_id="LINE-02",
        underperformance_dates=_dates_for_offsets(start_date, range(25, 32)),
        downtime_spike_line_id="LINE-03",
        downtime_spike_dates=_dates_for_offsets(start_date, range(42, 45)),
        scrap_increase_line_id="LINE-01",
        scrap_increase_dates=_dates_for_offsets(start_date, range(57, 62)),
        low_inventory_material_ids=("MAT-005", "MAT-012", "MAT-027", "MAT-038"),
        low_inventory_dates=_dates_for_offsets(start_date, range(70, 77)),
        incomplete_order_ids=incomplete_order_ids,
    )


def _dates_for_offsets(start_date: date, offsets: range) -> tuple[date, ...]:
    return tuple(start_date + timedelta(days=offset) for offset in offsets)


def _order_id(day_offset: int, line_index: int, shift_index: int) -> str:
    return f"MO-{day_offset + 1:03d}-{line_index + 1:02d}-{shift_index + 1}"


def _decimal(value: float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(_THREE_PLACES, rounding=ROUND_HALF_UP)


def generate_synthetic_data(
    *,
    seed: int = DEFAULT_SEED,
    start_date: date = DEFAULT_START_DATE,
    days: int = DEFAULT_DAYS,
) -> SyntheticDataBundle:
    """Generate contract-shaped synthetic datasets with controlled scenarios."""
    if days < DEFAULT_DAYS:
        raise ValueError(f"days must be at least {DEFAULT_DAYS} to include every scenario")

    rng = random.Random(seed)
    scenarios = _scenario_manifest(start_date)
    plan_rows: list[dict[str, object]] = []
    actual_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []

    for day_offset in range(days):
        production_date = start_date + timedelta(days=day_offset)
        for line_index, line_id in enumerate(LINE_IDS):
            for shift_index, shift_id in enumerate(SHIFT_IDS):
                product_index = (day_offset * 7 + line_index * 2 + shift_index) % len(
                    PRODUCT_IDS
                )
                order_id = _order_id(day_offset, line_index, shift_index)
                common = {
                    "production_date": production_date.isoformat(),
                    "line_id": line_id,
                    "shift_id": shift_id,
                    "order_id": order_id,
                    "product_id": PRODUCT_IDS[product_index],
                    "qty_unit": "ea",
                }

                planned_qty = (
                    850
                    + product_index * 18
                    + line_index * 55
                    + (90 if shift_id == "DAY" else 0)
                    + rng.randint(-35, 35)
                )
                planned_minutes = _decimal(480)

                if order_id in scenarios.incomplete_order_ids:
                    actual_ratio = rng.uniform(0.48, 0.62)
                elif (
                    line_id == scenarios.underperformance_line_id
                    and production_date in scenarios.underperformance_dates
                ):
                    actual_ratio = rng.uniform(0.68, 0.78)
                else:
                    actual_ratio = rng.uniform(0.94, 1.04)
                actual_qty = round(planned_qty * actual_ratio)

                if (
                    line_id == scenarios.downtime_spike_line_id
                    and production_date in scenarios.downtime_spike_dates
                ):
                    downtime_minutes = rng.randint(150, 210)
                else:
                    downtime_minutes = rng.randint(8, 35)
                residual_minutes = rng.randint(8, 22)
                runtime_minutes = 480 - downtime_minutes - residual_minutes

                if (
                    line_id == scenarios.scrap_increase_line_id
                    and production_date in scenarios.scrap_increase_dates
                ):
                    scrap_ratio = rng.uniform(0.10, 0.14)
                else:
                    scrap_ratio = rng.uniform(0.01, 0.03)
                scrap_qty = round(actual_qty * scrap_ratio)
                good_qty = actual_qty - scrap_qty

                plan_rows.append(
                    {
                        **common,
                        "planned_qty": planned_qty,
                        "planned_production_minutes": planned_minutes,
                    }
                )
                actual_rows.append(
                    {
                        **common,
                        "actual_qty": actual_qty,
                        "runtime_minutes": _decimal(runtime_minutes),
                        "downtime_minutes": _decimal(downtime_minutes),
                    }
                )
                quality_rows.append(
                    {
                        **common,
                        "good_qty": good_qty,
                        "scrap_qty": scrap_qty,
                    }
                )

    inventory_rows = _generate_inventory_rows(
        rng=rng,
        start_date=start_date,
        days=days,
        scenarios=scenarios,
    )

    return SyntheticDataBundle(
        production_plan=pd.DataFrame(plan_rows, columns=PRODUCTION_PLAN_COLUMNS),
        production_actual=pd.DataFrame(actual_rows, columns=PRODUCTION_ACTUAL_COLUMNS),
        quality=pd.DataFrame(quality_rows, columns=QUALITY_COLUMNS),
        inventory=pd.DataFrame(inventory_rows, columns=INVENTORY_COLUMNS),
        scenarios=scenarios,
        seed=seed,
        start_date=start_date,
        days=days,
    )


def _generate_inventory_rows(
    *,
    rng: random.Random,
    start_date: date,
    days: int,
    scenarios: ScenarioManifest,
) -> list[dict[str, object]]:
    units = ("ea", "kg", "m", "l")
    rows: list[dict[str, object]] = []

    for material_index, material_id in enumerate(MATERIAL_IDS):
        qty_unit = units[material_index % len(units)]
        safety_stock = 200 + material_index * 12
        replenishment_cycle = 7 + material_index % 5

        for day_offset in range(days):
            snapshot_date = start_date + timedelta(days=day_offset)
            cycle_remaining = replenishment_cycle - day_offset % replenishment_cycle
            normal_factor = 1.15 + 0.75 * cycle_remaining / replenishment_cycle
            normal_factor += rng.uniform(0.02, 0.12)

            is_low_inventory = (
                material_id in scenarios.low_inventory_material_ids
                and snapshot_date in scenarios.low_inventory_dates
            )
            factor = rng.uniform(0.55, 0.85) if is_low_inventory else normal_factor
            inventory_qty = safety_stock * factor

            if qty_unit == "ea":
                clean_inventory_qty: int | Decimal = round(inventory_qty)
                clean_safety_stock: int | Decimal = safety_stock
            else:
                clean_inventory_qty = _decimal(inventory_qty)
                clean_safety_stock = _decimal(safety_stock)

            rows.append(
                {
                    "snapshot_date": snapshot_date.isoformat(),
                    "material_id": material_id,
                    "qty_unit": qty_unit,
                    "inventory_qty": clean_inventory_qty,
                    "safety_stock": clean_safety_stock,
                }
            )

    return rows


def write_synthetic_csv(
    bundle: SyntheticDataBundle,
    output_dir: Path,
) -> dict[str, Path]:
    """Write canonical synthetic datasets to clearly labeled CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for dataset_name, frame in bundle.datasets().items():
        path = output_dir / f"synthetic_{dataset_name}.csv"
        frame.to_csv(path, index=False, lineterminator="\n")
        paths[dataset_name] = path
    return paths


def main() -> None:
    """Generate the default reproducible CSV sample set."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/samples/clean"),
        help="Directory for the four synthetic CSV files",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    write_synthetic_csv(generate_synthetic_data(seed=args.seed), args.output_dir)


if __name__ == "__main__":
    main()
