"""Streamlit runtime checks for the five service-backed dashboard areas."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from manufacturing_operations_intelligence.domain.analytics import KpiScope
from manufacturing_operations_intelligence.domain.anomalies import (
    AnomalyEntity,
    DetectionResult,
    SkippedRule,
)
from manufacturing_operations_intelligence.services.application import (
    AnomalyAnalysis,
    ManufacturingApplicationService,
)

APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def _area(app: AppTest):
    return next(widget for widget in app.radio if widget.label == "Area")


def test_dashboard_empty_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MOI_DATABASE_PATH", str(tmp_path / "empty.sqlite3"))
    app = AppTest.from_file(APP_FILE, default_timeout=10).run()
    assert not app.exception
    assert any("Load the synthetic demo" in item.value for item in app.info)
    next(
        widget for widget in app.button if widget.label == "Load synthetic demo data"
    ).click().run()
    assert not app.exception
    assert len(app.metric) == 6


def test_invalid_environment_boolean_is_actionable(monkeypatch) -> None:
    monkeypatch.setenv("MOI_AI_ENABLED", "maybe")
    app = AppTest.from_file(APP_FILE, default_timeout=10).run()
    assert not app.exception
    assert any("MOI_AI_ENABLED must be a boolean" in item.value for item in app.error)


@pytest.mark.parametrize("corrupt_file", [False, True])
def test_incompatible_database_is_actionable_instead_of_crashing(
    tmp_path: Path, monkeypatch, corrupt_file: bool
) -> None:
    database = tmp_path / "incompatible.sqlite3"
    if corrupt_file:
        database.write_bytes(b"not a SQLite database")
    else:
        with sqlite3.connect(database) as connection:
            connection.execute("PRAGMA user_version=99")
    monkeypatch.setenv("MOI_DATABASE_PATH", str(database))

    app = AppTest.from_file(APP_FILE, default_timeout=10).run()

    assert not app.exception
    assert any("incompatible schema" in item.value for item in app.error)


def test_five_areas_and_filters_render_from_sample_data(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "demo.sqlite3"
    service = ManufacturingApplicationService.from_path(database)
    assert service.load_sample_data().status == "accepted"
    monkeypatch.setenv("MOI_DATABASE_PATH", str(database))

    app = AppTest.from_file(APP_FILE, default_timeout=10).run()
    assert not app.exception
    assert len(app.metric) == 6
    assert any(item.label == "Completed orders" and item.value == "N/A" for item in app.metric)

    for name in ("Production", "Quality", "Inventory", "Reports & Insights"):
        _area(app).set_value(name).run()
        assert not app.exception
        assert any(item.value == name for item in app.header)

    _area(app).set_value("Production").run()
    next(
        widget for widget in app.multiselect if widget.label.startswith("Production lines")
    ).set_value(["LINE-02"])
    next(
        widget for widget in app.multiselect if widget.label.startswith("Finished products")
    ).set_value(["PRD-001"])
    app.run()
    assert not app.exception

    start = next(widget for widget in app.date_input if widget.label == "From")
    end = next(widget for widget in app.date_input if widget.label == "Through")
    start.set_value(date(2026, 1, 1))
    end.set_value(date(2026, 1, 2))
    app.run()
    assert not app.exception
    assert any("No production records match" in item.value for item in app.info)


@pytest.mark.parametrize(
    ("status", "completed", "skipped", "healthy"),
    [
        ("valid", 5, False, True),
        ("valid", 2, True, False),
        ("valid", 0, False, False),
        ("partial_coverage", 4, True, False),
        ("no_data", 0, False, False),
        ("unsupported_schema", 0, False, False),
        ("invalid_data", 0, False, False),
    ],
)
def test_alert_status_never_claims_all_clear_for_incomplete_checks(
    status, completed, skipped, healthy
) -> None:
    scope = KpiScope("2025-01-01", "2025-01-02")
    skipped_checks = (
        (
            SkippedRule(
                "LOW_INVENTORY",
                AnomalyEntity("material", "MAT-001"),
                scope.start_date,
                scope.end_date,
                "No eligible inventory snapshot.",
            ),
        )
        if skipped
        else ()
    )
    result = DetectionResult(status, (), skipped_checks, completed, None, scope, "B-1")
    analysis = AnomalyAnalysis("available", scope, SimpleNamespace(batch_id="B-1"), result)
    app = AppTest.from_string(
        "import streamlit as st\n"
        "from manufacturing_operations_intelligence.ui.app import _anomaly_panel\n"
        "_anomaly_panel(st.session_state['analysis'], 'B-1', full=False)"
    )
    app.session_state["analysis"] = analysis
    app.run()
    assert not app.exception
    assert bool(app.success) is healthy
    if skipped:
        assert any("incomplete" in item.value for item in app.warning)
        assert app.dataframe[0].value.iloc[0]["Reason"] == "No eligible inventory snapshot."
    elif not healthy:
        assert app.error or app.warning


def test_unconfigured_and_invalid_thresholds_are_actionable(tmp_path, monkeypatch) -> None:
    database = tmp_path / "alerts.sqlite3"
    service = ManufacturingApplicationService.from_path(database)
    service.load_sample_data()
    monkeypatch.setenv("MOI_DATABASE_PATH", str(database))
    app = AppTest.from_file(APP_FILE, default_timeout=10).run()
    assert any("Alerts have not been checked" in item.value for item in app.warning)
    assert not app.success
    for invalid in ("abc", "-1", "NaN", "Infinity"):
        app.text_input[0].set_value(invalid).run()
        assert not app.exception
        assert any("finite number" in item.value for item in app.error)
        assert any("Alerts have not been checked" in item.value for item in app.warning)
        assert not app.success
    app.text_input[0].set_value("120").run()
    assert not app.exception
    assert not app.error
    assert any("operational alerts" in item.value for item in app.warning)


def test_replacement_requires_acknowledgement_and_resets_after_attempt(tmp_path, monkeypatch):
    database = tmp_path / "replacement.sqlite3"
    service = ManufacturingApplicationService.from_path(database)
    original = service.load_sample_data().persistence.identity.batch_id
    monkeypatch.setenv("MOI_DATABASE_PATH", str(database))
    app = AppTest.from_file(APP_FILE, default_timeout=10).run()

    def demo():
        return next(b for b in app.button if b.label == "Load synthetic demo data")

    def upload():
        return next(b for b in app.button if b.label == "Validate and activate upload")

    assert demo().disabled
    assert upload().disabled
    assert service.get_filter_options().identity.batch_id == original
    next(c for c in app.checkbox if "loading demo data" in c.label).check().run()
    assert not demo().disabled
    assert upload().disabled
    demo().click().run()
    assert not app.exception
    assert any("already active" in item.value for item in app.success)
    assert demo().disabled
    assert service.get_filter_options().identity.batch_id == original

    next(c for c in app.checkbox if "this upload" in c.label).check().run()
    assert not upload().disabled
    upload().click().run()  # Missing files: rejected, original data must remain active.
    assert not app.exception
    assert any("Upload not activated" in item.value for item in app.error)
    assert upload().disabled
    assert service.get_filter_options().identity.batch_id == original


def test_import_feedback_exposes_normalization_and_source_locations(tmp_path, monkeypatch):
    from dataclasses import replace

    database = tmp_path / "feedback.sqlite3"
    service = ManufacturingApplicationService.from_path(database)
    accepted = service.load_sample_data()
    monkeypatch.setenv("MOI_DATABASE_PATH", str(database))
    app = AppTest.from_file(APP_FILE, default_timeout=10)
    app.session_state["upload_feedback"] = accepted
    app.run()
    assert not app.exception
    assert any("Format normalizations:" in item.value for item in app.caption)
    audit = next(df.value for df in app.dataframe if "Normalized value" in df.value.columns)
    issue = next(issue for issue in accepted.validation.issues if issue.severity == "INFO")
    assert audit.iloc[0]["Original value"] == issue.original
    assert audit.iloc[0]["Normalized value"] == issue.normalized
    assert audit.iloc[0]["File"] == issue.filename
    assert len(audit) == 100
    app.number_input[0].set_value(2).run()
    assert not app.exception
    assert any("Showing 101–200" in item.value for item in app.caption)

    # Exercise workbook and cross-file locations from structured validation results.
    error = replace(
        issue,
        severity="ERROR",
        sheet="production_plan",
        field="planned_qty",
        row=7,
        reason="Quantity must not be negative.",
        original="-1",
        normalized=None,
        correction="Correct the source quantity.",
        counterpart_dataset="production_actual",
        counterpart_filename="actual.csv",
        counterpart_rows=(9,),
    )
    rejected = replace(
        accepted,
        status="rejected",
        persistence=None,
        validation=replace(
            accepted.validation,
            attempt_id="rejected",
            accepted=False,
            status="rejected",
            issues=(error,),
            error_count=1,
            affected_row_count=1,
            normalization_action_count=0,
            unevaluated_rows=2,
        ),
    )
    app.session_state["upload_feedback"] = rejected
    app.run()
    assert not app.exception
    assert any("2 source rows were not checked" in item.value for item in app.warning)
    table = next(df.value for df in app.dataframe if "Original value" in df.value.columns)
    assert table.iloc[0]["Sheet"] == "production_plan"
    assert table.iloc[0]["Row"] == 7
    assert table.iloc[0]["Field"] == "planned_qty"
    assert table.iloc[0]["Related rows"] == "9"
    assert table.iloc[0]["How to fix it"] == "Correct the source quantity."

    app.session_state["upload_feedback"] = replace(
        accepted,
        status="persistence_failed",
        persistence=None,
        persistence_error="internal-storage-diagnostic",
    )
    app.run()
    assert not app.exception
    assert any("Check that local storage" in item.value for item in app.error)
    assert all("internal-storage-diagnostic" not in item.value for item in app.error)
