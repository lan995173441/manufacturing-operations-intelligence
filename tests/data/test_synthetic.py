"""Contract and scenario tests for deterministic synthetic manufacturing data."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from manufacturing_operations_intelligence.data.synthetic import (
    LINE_IDS,
    MATERIAL_IDS,
    PRODUCT_IDS,
    generate_synthetic_data,
    write_synthetic_csv,
)

PRODUCTION_KEY = ["production_date", "line_id", "shift_id"]
COMMON_COLUMNS = [
    "production_date",
    "line_id",
    "shift_id",
    "order_id",
    "product_id",
    "qty_unit",
]


@pytest.fixture(scope="module")
def bundle():
    return generate_synthetic_data()


def test_schema_scope_and_record_counts(bundle) -> None:
    assert list(bundle.production_plan.columns) == [
        *COMMON_COLUMNS,
        "planned_qty",
        "planned_production_minutes",
    ]
    assert list(bundle.production_actual.columns) == [
        *COMMON_COLUMNS,
        "actual_qty",
        "runtime_minutes",
        "downtime_minutes",
    ]
    assert list(bundle.quality.columns) == [*COMMON_COLUMNS, "good_qty", "scrap_qty"]
    assert list(bundle.inventory.columns) == [
        "snapshot_date",
        "material_id",
        "qty_unit",
        "inventory_qty",
        "safety_stock",
    ]

    expected_production_rows = 90 * 3 * 2
    assert len(bundle.production_plan) == expected_production_rows
    assert len(bundle.production_actual) == expected_production_rows
    assert len(bundle.quality) == expected_production_rows
    assert len(bundle.inventory) == 90 * 40
    assert bundle.production_plan["production_date"].nunique() == 90
    assert set(bundle.production_plan["line_id"]) == set(LINE_IDS)
    assert set(bundle.production_plan["product_id"]) == set(PRODUCT_IDS)
    assert set(bundle.inventory["material_id"]) == set(MATERIAL_IDS)


def test_referential_consistency(bundle) -> None:
    production_frames = [bundle.production_plan, bundle.production_actual, bundle.quality]
    key_sets = [
        set(frame[PRODUCTION_KEY].itertuples(index=False, name=None))
        for frame in production_frames
    ]
    assert key_sets[0] == key_sets[1] == key_sets[2]
    assert all(not frame.duplicated(PRODUCTION_KEY).any() for frame in production_frames)

    expected_common = bundle.production_plan[COMMON_COLUMNS].sort_values(PRODUCTION_KEY)
    for frame in production_frames[1:]:
        actual_common = frame[COMMON_COLUMNS].sort_values(PRODUCTION_KEY)
        assert_frame_equal(
            expected_common.reset_index(drop=True),
            actual_common.reset_index(drop=True),
        )

    order_product_counts = bundle.production_plan.groupby("order_id")["product_id"].nunique()
    assert order_product_counts.max() == 1
    assert not bundle.inventory.duplicated(["snapshot_date", "material_id"]).any()
    assert bundle.inventory.groupby("material_id")["qty_unit"].nunique().max() == 1


def test_values_follow_contract_ranges(bundle) -> None:
    plan = bundle.production_plan
    actual = bundle.production_actual
    quality = bundle.quality
    inventory = bundle.inventory

    assert plan["planned_qty"].between(0, 1_000_000_000).all()
    assert actual["actual_qty"].between(0, 1_000_000_000).all()
    assert quality[["good_qty", "scrap_qty"]].ge(0).all().all()
    assert (quality["good_qty"] + quality["scrap_qty"] == actual["actual_qty"]).all()

    time_sum = actual["runtime_minutes"] + actual["downtime_minutes"]
    assert (time_sum <= plan["planned_production_minutes"]).all()
    daily_line_minutes = plan.groupby(["production_date", "line_id"])[
        "planned_production_minutes"
    ].sum()
    assert (daily_line_minutes <= Decimal("1440.000")).all()

    assert inventory[["inventory_qty", "safety_stock"]].ge(0).all().all()
    ea_rows = inventory[inventory["qty_unit"] == "ea"]
    assert all(Decimal(str(value)) % 1 == 0 for value in ea_rows["inventory_qty"])
    assert set(inventory["qty_unit"]) == {"ea", "kg", "m", "l"}


def test_generation_is_deterministic() -> None:
    first = generate_synthetic_data(seed=2606)
    second = generate_synthetic_data(seed=2606)
    different_seed = generate_synthetic_data(seed=2607)

    for dataset_name in first.datasets():
        assert_frame_equal(first.datasets()[dataset_name], second.datasets()[dataset_name])
    assert first.scenarios == second.scenarios
    assert not first.production_actual.equals(different_seed.production_actual)


def test_controlled_abnormal_scenarios_are_present(bundle) -> None:
    scenarios = bundle.scenarios
    underperformance_dates = [date.isoformat() for date in scenarios.underperformance_dates]
    downtime_spike_dates = [date.isoformat() for date in scenarios.downtime_spike_dates]
    scrap_increase_dates = [date.isoformat() for date in scenarios.scrap_increase_dates]
    joined = bundle.production_plan.merge(
        bundle.production_actual,
        on=COMMON_COLUMNS,
        validate="one_to_one",
    ).merge(bundle.quality, on=COMMON_COLUMNS, validate="one_to_one")

    underperformance = joined[
        (joined["line_id"] == scenarios.underperformance_line_id)
        & joined["production_date"].isin(underperformance_dates)
    ]
    normal_output = joined[
        ~joined["production_date"].isin(underperformance_dates)
        & ~joined["order_id"].isin(scenarios.incomplete_order_ids)
    ]
    assert underperformance["actual_qty"].sum() / underperformance["planned_qty"].sum() < 0.80
    assert normal_output["actual_qty"].sum() / normal_output["planned_qty"].sum() > 0.90

    downtime_spikes = joined[
        (joined["line_id"] == scenarios.downtime_spike_line_id)
        & joined["production_date"].isin(downtime_spike_dates)
    ]
    assert downtime_spikes["downtime_minutes"].min() >= Decimal("150.000")

    scrap_increase = joined[
        (joined["line_id"] == scenarios.scrap_increase_line_id)
        & joined["production_date"].isin(scrap_increase_dates)
    ]
    assert scrap_increase["scrap_qty"].sum() / scrap_increase["actual_qty"].sum() >= 0.10

    low_inventory = bundle.inventory[
        bundle.inventory["material_id"].isin(scenarios.low_inventory_material_ids)
        & bundle.inventory["snapshot_date"].isin(
            date.isoformat() for date in scenarios.low_inventory_dates
        )
    ]
    assert len(low_inventory) == len(scenarios.low_inventory_material_ids) * len(
        scenarios.low_inventory_dates
    )
    assert (low_inventory["inventory_qty"] < low_inventory["safety_stock"]).all()

    incomplete = joined[joined["order_id"].isin(scenarios.incomplete_order_ids)]
    assert set(incomplete["order_id"]) == set(scenarios.incomplete_order_ids)
    assert (incomplete["actual_qty"] / incomplete["planned_qty"] < 0.65).all()


def test_csv_writer_preserves_four_canonical_datasets(bundle, tmp_path) -> None:
    paths = write_synthetic_csv(bundle, tmp_path)
    assert set(paths) == {"production_plan", "production_actual", "quality", "inventory"}
    assert all(path.name.startswith("synthetic_") for path in paths.values())
    for dataset_name, path in paths.items():
        written = pd.read_csv(path)
        assert list(written.columns) == list(bundle.datasets()[dataset_name].columns)
        assert len(written) == len(bundle.datasets()[dataset_name])
