"""Optional management narrative over already-calculated report facts."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from typing import Any, Literal
from urllib import error, request

from manufacturing_operations_intelligence.data.repository import BatchIdentity
from manufacturing_operations_intelligence.domain.analytics import KpiScope
from manufacturing_operations_intelligence.reporting.renderers import LABELS, ReportPayload

SummaryStatus = Literal[
    "ai_draft", "fallback_disabled", "fallback_missing_key", "fallback_timeout",
    "fallback_api_failure", "fallback_malformed", "fallback_unsupported_claim",
]
Provider = Callable[[Mapping[str, object], str, str], str]
_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {"type": "array", "items": {"type": "string"}},
        "management_attention": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["observations", "management_attention"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ManagementSummary:
    status: SummaryStatus
    identity: BatchIdentity
    scope: KpiScope
    definition_version: str
    observations: tuple[str, ...]
    management_attention: tuple[str, ...]
    limitations: tuple[str, ...]


def _number(value: Fraction | Decimal) -> str:
    if isinstance(value, Decimal):
        return str(value)
    with localcontext() as context:
        context.prec = 40
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
    return str(decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def project_facts(payload: ReportPayload) -> dict[str, object]:
    """Allowlist bounded aggregates; no raw records or source references cross this boundary."""
    definition = payload.metrics["KPI-PA"].definition_version
    if any(
        metric.batch_id != payload.identity.batch_id
        or metric.fingerprint != payload.identity.fingerprint
        or metric.scope != payload.scope
        or metric.definition_version != definition
        for metric in payload.metrics.values()
    ):
        raise ValueError("Summary KPI facts do not match batch and scope.")
    if payload.detection is not None and (
        payload.detection.batch_id != payload.identity.batch_id
        or payload.detection.scope != payload.scope
    ):
        raise ValueError("Summary anomaly facts do not match batch and scope.")
    metrics = {
        key: {
            "label": LABELS[key], "status": metric.status,
            "display_value": metric.display_value if metric.status == "valid" else None,
            "unit": metric.unit, "reason": metric.reason,
        }
        for key, metric in payload.metrics.items() if key in LABELS
    }
    detection = payload.detection
    anomalies = []
    if detection is not None:
        severity_rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        for index, item in enumerate(sorted(
            detection.anomalies,
            key=lambda row: (severity_rank[row.severity], row.date_start, row.type),
        )[:8], start=1):
            anomalies.append({
                "fact_id": f"ANOM-{index:03d}", "type": item.type, "severity": item.severity,
                "entity_kind": item.entity.kind, "date_start": item.date_start,
                "date_end": item.date_end, "observed_value": _number(item.observed_value),
                "threshold": _number(item.threshold), "unit": item.unit,
            })
    recent_daily = [
        {"fact_id": f"DAY-{item.group}", "date": item.group,
         "planned_qty": item.planned_qty,
         "actual_qty": item.actual_qty, "good_qty": item.good_qty,
         "scrap_qty": item.scrap_qty, "downtime_minutes": str(item.downtime_minutes)}
        for item in payload.series.daily[-7:]
    ]
    return {
        "identity": {
            "batch_id": payload.identity.batch_id,
            "contract_version": payload.identity.contract_version,
            "definition_version": payload.metrics["KPI-PA"].definition_version,
        },
        "date_range": {"start": payload.scope.start_date, "end": payload.scope.end_date},
        "filters": {
            "line_ids": payload.scope.line_ids or (),
            "product_ids": payload.scope.product_ids or (),
            "shift_ids": payload.scope.shift_ids or (),
        },
        "kpis": metrics,
        "anomalies": {
            "status": detection.status if detection else "not_evaluated",
            "count": detection.anomaly_count if detection else None,
            "skipped_count": detection.skipped_count if detection else None,
            "selected": anomalies,
        },
        "trend_summaries": {"recent_daily": recent_daily, "coverage": "last seven selected dates"},
        "limitations": [
            "Inventory is site-wide as of the end date; line and product filters do not apply.",
            "Order completion and schedule adherence are unavailable under this data contract.",
            "Selected anomalies are a capped preview; count covers all detected anomalies.",
        ],
    }


def _fallback(facts: Mapping[str, object]) -> tuple[tuple[str, ...], ...]:
    dates, kpis, anomaly = facts["date_range"], facts["kpis"], facts["anomalies"]
    assert isinstance(dates, dict) and isinstance(kpis, dict) and isinstance(anomaly, dict)

    def value(key: str) -> str:
        item = kpis[key]
        assert isinstance(item, dict)
        return str(item["display_value"] or "N/A")

    observations = (
        f"For {dates['start']} to {dates['end']}, production attainment is {value('KPI-PA')}, "
        f"good yield is {value('KPI-GY')}, and scrap rate is {value('KPI-SR')}.",
        f"Total downtime is {value('KPI-TD')}; materials below safety stock: {value('KPI-IR')}.",
    )
    if anomaly["status"] == "not_evaluated":
        attention = ("Anomaly rules were not evaluated; configure the downtime threshold.",)
    else:
        attention = (
            f"Review {anomaly['count']} detected anomalies. "
            f"Skipped checks: {anomaly['skipped_count']}.",
        )
    return observations, attention, tuple(str(item) for item in facts["limitations"])


def _fact_texts(facts: Mapping[str, object]) -> dict[str, str]:
    """Only this deterministic renderer may attach supplied values to metric names."""
    texts = {}
    for key, item in facts["kpis"].items():
        value = item["display_value"]
        texts[key] = (
            f"{item['label']}: {value}." if value is not None
            else f"{item['label']}: unavailable ({item['reason'] or item['status']})."
        )
    for item in facts["anomalies"]["selected"]:
        texts[item["fact_id"]] = (
            f"{item['severity']} {item['type'].replace('_', ' ').lower()} on "
            f"{item['date_start']}: observed {item['observed_value']} {item['unit']}; "
            f"threshold {item['threshold']} {item['unit']}."
        )
    for item in facts["trend_summaries"]["recent_daily"]:
        texts[item["fact_id"]] = (
            f"{item['date']}: planned {item['planned_qty']} ea, actual "
            f"{item['actual_qty']} ea, good {item['good_qty']} ea, "
            f"scrap {item['scrap_qty']} ea, downtime {item['downtime_minutes']} line-minutes."
        )
    return texts


def _validated_draft(raw: str, facts: Mapping[str, object]) -> tuple[tuple[str, ...], ...]:
    try:
        draft = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Malformed AI response") from exc
    if not isinstance(draft, dict) or set(draft) != set(_SCHEMA["required"]):
        raise ValueError("Malformed AI response")
    texts = _fact_texts(facts)
    sections = []
    for key in _SCHEMA["required"]:
        values = draft[key]
        if (
            not isinstance(values, list) or len(values) > 4
            or (key == "observations" and not values)
            or len(values) != len(set(values))
        ):
            raise ValueError("Malformed AI response")
        if any(not isinstance(item, str) or item not in texts for item in values):
            raise ArithmeticError("Unsupported fact reference")
        sections.append(tuple(texts[item] for item in values))
    return (*sections, tuple(str(item) for item in facts["limitations"]))


def openai_responses_provider(facts: Mapping[str, object], api_key: str, model: str) -> str:
    """Small bounded HTTP adapter; only allowlisted facts are sent to the provider."""
    body = {
        "model": model,
        "instructions": (
            "Choose up to four fact IDs for observations and up to four for management_attention. "
            "Use only KPI IDs, selected anomaly fact_id values, or recent_daily fact_id values "
            "from the input. Return IDs only in the JSON arrays, with no prose, numbers, causes, "
            "compliance claims, or invented IDs. Prioritize important supplied facts."
        ),
        "input": json.dumps(facts, ensure_ascii=False, default=list),
        "text": {"format": {"type": "json_schema", "name": "management_summary",
                            "strict": True, "schema": _SCHEMA}},
        "max_output_tokens": 650,
        "store": False,
    }
    wire = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(wire, timeout=12) as response:
        result: Any = json.loads(response.read(32769))
    if not isinstance(result, dict) or result.get("status") != "completed":
        raise ValueError("Unusable AI response")
    texts = [
        part.get("text")
        for item in result.get("output", [])
        if isinstance(item, dict) and item.get("type") == "message"
        for part in item.get("content", [])
        if isinstance(part, dict) and part.get("type") == "output_text"
    ]
    if len(texts) != 1 or not isinstance(texts[0], str):
        raise ValueError("Unusable AI response")
    return texts[0]


def generate_management_summary(
    payload: ReportPayload, *, enabled: bool, api_key: str | None,
    model: str, provider: Provider = openai_responses_provider,
) -> ManagementSummary:
    facts = project_facts(payload)
    fallback = _fallback(facts)
    sections = fallback
    status: SummaryStatus
    if not enabled:
        status = "fallback_disabled"
    elif not api_key or not api_key.strip():
        status = "fallback_missing_key"
    else:
        try:
            sections = _validated_draft(provider(facts, api_key, model), facts)
            status = "ai_draft"
        except TimeoutError:
            status = "fallback_timeout"
        except error.URLError as exc:
            status = (
                "fallback_timeout" if isinstance(exc.reason, TimeoutError)
                else "fallback_api_failure"
            )
        except (error.HTTPError, OSError):
            status = "fallback_api_failure"
        except ArithmeticError:
            status = "fallback_unsupported_claim"
        except (ValueError, TypeError, KeyError):
            status = "fallback_malformed"
        except Exception:
            # A replaceable provider must not leak exception text (or secrets) to the UI.
            status = "fallback_api_failure"
    return ManagementSummary(
        status, payload.identity, payload.scope, payload.metrics["KPI-PA"].definition_version,
        *sections,
    )
