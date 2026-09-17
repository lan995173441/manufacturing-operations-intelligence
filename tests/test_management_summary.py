"""Optional AI summary boundary; all provider and HTTP responses are mocked."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from urllib import error

import pytest
from streamlit.testing.v1 import AppTest

from manufacturing_operations_intelligence.domain.analytics import KpiScope
from manufacturing_operations_intelligence.services.application import (
    ManufacturingApplicationService,
)
from manufacturing_operations_intelligence.summaries import (
    generate_management_summary,
    openai_responses_provider,
    project_facts,
)

SCOPE = KpiScope("2025-01-01", "2025-03-31", line_ids=("LINE-02",))


@pytest.fixture
def payload(tmp_path: Path):
    service = ManufacturingApplicationService.from_path(
        tmp_path / "summary.sqlite3", downtime_above_minutes=Decimal("120")
    )
    assert service.load_sample_data().status == "accepted"
    return service.get_report_payload(SCOPE)


def test_projection_is_bounded_calculated_facts_only(payload) -> None:
    facts = project_facts(payload)
    assert facts["identity"]["batch_id"] == payload.identity.batch_id
    assert facts["kpis"]["KPI-PA"]["display_value"] == payload.metrics["KPI-PA"].display_value
    assert facts["kpis"]["KPI-CO"]["display_value"] is None
    assert facts["anomalies"]["count"] == payload.detection.anomaly_count
    assert len(facts["anomalies"]["selected"]) <= 8
    assert len(facts["trend_summaries"]["recent_daily"]) <= 7
    wire = json.dumps(facts)
    for forbidden in ("source_refs", "source_row", "normalized_records", "order_id", "sql"):
        assert forbidden not in wire


def test_disabled_and_missing_key_use_deterministic_fallback_without_provider(payload) -> None:
    def forbidden(*_args):
        raise AssertionError("Provider must not be called")

    disabled = generate_management_summary(
        payload, enabled=False, api_key="secret", model="test", provider=forbidden
    )
    missing = generate_management_summary(
        payload, enabled=True, api_key=None, model="test", provider=forbidden
    )
    assert disabled.status == "fallback_disabled"
    assert missing.status == "fallback_missing_key"
    assert disabled.observations == missing.observations
    assert payload.metrics["KPI-PA"].display_value in missing.observations[0]


def test_valid_mocked_ai_draft_is_labeled_and_scoped(payload) -> None:
    seen = {}

    def provider(facts, key, model):
        seen.update(facts=facts, key=key, model=model)
        return json.dumps({
            "observations": ["KPI-PA"],
            "management_attention": ["KPI-SR"],
        })

    result = generate_management_summary(
        payload, enabled=True, api_key="test-secret", model="test-model", provider=provider
    )
    assert result.status == "ai_draft"
    assert result.identity == payload.identity and result.scope == SCOPE
    assert result.definition_version == payload.metrics["KPI-PA"].definition_version
    assert seen["key"] == "test-secret" and seen["model"] == "test-model"
    assert seen["facts"]["date_range"] == {"start": SCOPE.start_date, "end": SCOPE.end_date}
    assert payload.metrics["KPI-PA"].display_value in result.observations[0]
    assert any("Order completion" in item for item in result.limitations)


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (TimeoutError("secret"), "fallback_timeout"),
        (error.URLError(TimeoutError("secret")), "fallback_timeout"),
        (error.URLError("network secret"), "fallback_api_failure"),
        (RuntimeError("secret"), "fallback_api_failure"),
    ],
)
def test_provider_failures_do_not_leak_and_keep_fallback(payload, failure, status) -> None:
    def provider(*_args):
        raise failure

    result = generate_management_summary(
        payload, enabled=True, api_key="secret", model="test", provider=provider
    )
    assert result.status == status
    assert "secret" not in repr(result)
    assert result.observations


@pytest.mark.parametrize("response", ["not json", "{}", '{"observations": "text"}'])
def test_malformed_model_drafts_fall_back(payload, response: str) -> None:
    result = generate_management_summary(
        payload, enabled=True, api_key="secret", model="test",
        provider=lambda *_args: response,
    )
    assert result.status == "fallback_malformed"


def test_unsupported_fact_reference_falls_back(payload) -> None:
    response = json.dumps({
        "observations": ["KPI-FAKE"],
        "management_attention": [],
    })
    result = generate_management_summary(
        payload, enabled=True, api_key="secret", model="test",
        provider=lambda *_args: response,
    )
    assert result.status == "fallback_unsupported_claim"
    assert "KPI-FAKE" not in repr(result)


def test_false_numerical_and_operational_claims_cannot_be_accepted(payload) -> None:
    response = json.dumps({
        "observations": ["Scrap rate is 98.01% due to equipment failure."],
        "management_attention": ["All orders finished on time."],
    })
    result = generate_management_summary(
        payload, enabled=True, api_key="secret", model="test",
        provider=lambda *_args: response,
    )
    assert result.status == "fallback_unsupported_claim"
    assert "equipment failure" not in repr(result)
    assert "finished on time" not in repr(result)


def test_mismatched_calculated_identity_is_rejected(payload) -> None:
    metrics = dict(payload.metrics)
    metrics["KPI-PA"] = replace(metrics["KPI-PA"], batch_id="different")
    with pytest.raises(ValueError, match="do not match"):
        project_facts(replace(payload, metrics=metrics))


def test_service_reads_environment_only_on_explicit_request(payload, tmp_path, monkeypatch) -> None:
    service = ManufacturingApplicationService.from_path(tmp_path / "service.sqlite3")
    assert service.load_sample_data().status == "accepted"
    monkeypatch.setenv("MOI_AI_ENABLED", "true")
    monkeypatch.delenv("MOI_AI_API_KEY", raising=False)
    result = service.get_management_summary(
        SCOPE, provider=lambda *_args: pytest.fail("API called")
    )
    assert result.status == "fallback_missing_key"
    assert result.identity.batch_id == service.get_report_payload(SCOPE).identity.batch_id


def test_http_adapter_uses_bounded_responses_request_with_no_storage(monkeypatch) -> None:
    captured = {}
    draft = json.dumps({"observations": ["KPI-PA"], "management_attention": []})

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit):
            assert limit == 32769
            return json.dumps({
                "status": "completed", "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": draft}
                ]}],
            }).encode()

    def fake_urlopen(wire, timeout):
        captured["wire"] = wire
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "manufacturing_operations_intelligence.summaries.management.request.urlopen", fake_urlopen
    )
    result = openai_responses_provider({"kpis": {}}, "test-secret", "test-model")
    body = json.loads(captured["wire"].data)
    assert result == draft
    assert captured["timeout"] == 12
    assert captured["wire"].full_url == "https://api.openai.com/v1/responses"
    assert captured["wire"].get_header("Authorization") == "Bearer test-secret"
    assert body["store"] is False and body["max_output_tokens"] == 650
    assert "test-secret" not in captured["wire"].data.decode()


def test_reports_page_can_generate_summary_offline(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "ui-summary.sqlite3"
    service = ManufacturingApplicationService.from_path(database)
    assert service.load_sample_data().status == "accepted"
    monkeypatch.setenv("MOI_DATABASE_PATH", str(database))
    monkeypatch.setenv("MOI_AI_ENABLED", "false")
    monkeypatch.delenv("MOI_AI_API_KEY", raising=False)
    app_file = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(app_file, default_timeout=10).run()
    next(widget for widget in app.radio if widget.label == "Area").set_value(
        "Reports & Insights"
    ).run()
    next(
        widget for widget in app.button if widget.label == "Generate management summary"
    ).click().run()
    assert not app.exception
    assert any("Deterministic offline summary" in item.value for item in app.info)
    assert any("Observations" in item.value for item in app.markdown)
    summary = app.session_state["prepared_summary"][1]
    app.session_state["prepared_summary"] = (("old-definition",), summary)
    app.run()
    assert "prepared_summary" not in app.session_state
