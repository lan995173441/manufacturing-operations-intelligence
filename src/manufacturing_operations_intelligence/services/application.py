"""High-level application services coordinating ingestion, persistence and analysis."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from reportlab.platypus.doctemplate import LayoutError

from manufacturing_operations_intelligence.data.readers import MAX_BYTES
from manufacturing_operations_intelligence.data.repository import (
    BatchIdentity,
    ReplaceOutcome,
    RepositoryError,
    SQLiteRepository,
)
from manufacturing_operations_intelligence.domain.analytics import (
    DashboardSeries,
    KpiResult,
    KpiScope,
    calculate_dashboard_data,
)
from manufacturing_operations_intelligence.domain.anomalies import (
    DetectionResult,
    RuleConfig,
    detect_anomalies,
)
from manufacturing_operations_intelligence.domain.validation import ValidationResult
from manufacturing_operations_intelligence.reporting import (
    ReportArtifacts,
    ReportPayload,
    render_excel,
    render_pdf,
)
from manufacturing_operations_intelligence.services.ingestion import (
    ingest_csv_batch,
    ingest_excel_workbook,
)
from manufacturing_operations_intelligence.settings import Settings
from manufacturing_operations_intelligence.summaries import (
    ManagementSummary,
    Provider,
    generate_management_summary,
    openai_responses_provider,
)

MAX_UPLOAD_BYTES = MAX_BYTES

UploadStatus = Literal["accepted", "rejected", "persistence_failed"]
AnalysisStatus = Literal["available", "no_active_batch", "rules_not_configured"]


class ApplicationServiceError(ValueError):
    """A caller supplied an incomplete or contradictory service request."""


@dataclass(frozen=True)
class UploadProcessingResult:
    status: UploadStatus
    validation: ValidationResult
    persistence: ReplaceOutcome | None
    persistence_error: str | None = None


@dataclass(frozen=True)
class MetricsAnalysis:
    status: AnalysisStatus
    scope: KpiScope
    identity: BatchIdentity | None
    metrics: dict[str, KpiResult]
    series: DashboardSeries = DashboardSeries()


@dataclass(frozen=True)
class FilterOptions:
    identity: BatchIdentity
    start_date: str
    end_date: str
    line_ids: tuple[str, ...]
    product_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnomalyAnalysis:
    status: AnalysisStatus
    scope: KpiScope
    identity: BatchIdentity | None
    detection: DetectionResult | None


class ManufacturingApplicationService:
    """UI-facing façade; all lower-level orchestration remains inside this layer."""

    def __init__(self, repository: SQLiteRepository, rule_config: RuleConfig | None = None) -> None:
        self._repository = repository
        self._rule_config = rule_config
        try:
            self._repository.initialize()
        except (RepositoryError, sqlite3.DatabaseError, OSError) as exc:
            raise ApplicationServiceError(
                "Local data store is unavailable or has an incompatible schema. "
                "Check the configured database path; do not overwrite an existing database."
            ) from exc

    @classmethod
    def from_path(
        cls, database_path: str | Path, *, downtime_above_minutes: Decimal | None = None
    ) -> ManufacturingApplicationService:
        """Build the local service without exposing repository setup to UI code."""
        rules = RuleConfig(downtime_above_minutes) if downtime_above_minutes is not None else None
        return cls(SQLiteRepository(database_path), rules)

    def get_available_scope(self) -> KpiScope | None:
        """Return the active batch's observed production-date bounds, if present."""
        options = self.get_filter_options()
        return KpiScope(options.start_date, options.end_date) if options else None

    def get_filter_options(self) -> FilterOptions | None:
        """Offer only lines and products present in the active accepted batch."""
        batch = self._load_batch()
        if batch is None or not batch.production_plan:
            return None
        values = [row.values for row in batch.production_plan]
        dates = [item["production_date"] for item in values]
        return FilterOptions(
            batch.identity,
            min(dates),
            max(dates),
            tuple(sorted({item["line_id"] for item in values})),
            tuple(sorted({item["product_id"] for item in values})),
        )

    def load_sample_data(self, directory: str | Path | None = None) -> UploadProcessingResult:
        """Activate the repository's clearly labeled synthetic CSV example batch."""
        root = (
            Path(directory)
            if directory
            else Path(__file__).resolve().parents[3] / "data/samples/clean"
        )
        files = {}
        for dataset in ("production_plan", "production_actual", "quality", "inventory"):
            path = root / f"synthetic_{dataset}.csv"
            if not path.is_file():
                raise ApplicationServiceError(f"Sample file is unavailable: {path.name}.")
            try:
                files[dataset] = (path.name, path.read_bytes())
            except OSError as exc:
                raise ApplicationServiceError(
                    f"Sample file could not be read: {path.name}."
                ) from exc
        return self.process_uploaded_data(csv_files=files)

    def process_uploaded_data(
        self,
        *,
        csv_files: Mapping[str, tuple[str, bytes]] | None = None,
        workbook: tuple[str, bytes] | None = None,
    ) -> UploadProcessingResult:
        """Validate one complete upload and atomically make it the active dataset."""
        if (csv_files is None) == (workbook is None):
            raise ApplicationServiceError(
                "Provide exactly one complete CSV batch or one Excel workbook."
            )
        validation = (
            ingest_csv_batch(csv_files)
            if csv_files is not None
            else ingest_excel_workbook(*workbook)
        )
        if not validation.accepted:
            return UploadProcessingResult("rejected", validation, None)
        try:
            persistence = self._repository.replace_demo_dataset(validation)
        except (RepositoryError, sqlite3.DatabaseError, OSError):
            return UploadProcessingResult(
                "persistence_failed", validation, None,
                "The validated upload could not be saved to the local data store.",
            )
        return UploadProcessingResult("accepted", validation, persistence)

    def get_overview_metrics(self, scope: KpiScope) -> MetricsAnalysis:
        """Return all documented KPI results for the selected business scope."""
        return self._metrics(
            scope,
            (
                "KPI-PA",
                "KPI-GY",
                "KPI-SR",
                "KPI-TD",
                "KPI-CO",
                "KPI-SA",
                "KPI-IR",
                "KPI-OL",
            ),
        )

    def get_production_analysis(self, scope: KpiScope) -> MetricsAnalysis:
        """Return production attainment, downtime and line-output results."""
        return self._metrics(scope, ("KPI-PA", "KPI-TD", "KPI-OL"))

    def get_quality_analysis(self, scope: KpiScope) -> MetricsAnalysis:
        """Return final-disposition quality measures."""
        return self._metrics(scope, ("KPI-GY", "KPI-SR"))

    def get_inventory_analysis(self, scope: KpiScope) -> MetricsAnalysis:
        """Return the as-of inventory risk result for the selected material scope."""
        return self._metrics(scope, ("KPI-IR",))

    def get_anomalies(self, scope: KpiScope) -> AnomalyAnalysis:
        """Return deterministic exceptions derived from the active validated batch."""
        batch = self._load_batch()
        if batch is None:
            return AnomalyAnalysis("no_active_batch", scope, None, None)
        if self._rule_config is None:
            return AnomalyAnalysis("rules_not_configured", scope, batch.identity, None)
        return AnomalyAnalysis(
            "available",
            scope,
            batch.identity,
            detect_anomalies(batch, scope, self._rule_config),
        )

    def get_report_payload(self, scope: KpiScope) -> ReportPayload:
        """Calculate one report scope from a single coherent active-batch read."""
        batch = self._load_batch()
        if batch is None:
            raise ApplicationServiceError("Load a validated dataset before generating reports.")
        calculated = calculate_dashboard_data(batch, scope)
        if any(metric.status == "invalid_data" for metric in calculated.metrics.values()):
            raise ApplicationServiceError(
                "Active data is invalid; report generation is unavailable."
            )
        detection = (
            detect_anomalies(batch, scope, self._rule_config)
            if self._rule_config is not None
            else None
        )
        if detection is not None and detection.status == "invalid_data":
            raise ApplicationServiceError(
                "Anomaly inputs are invalid; report generation is unavailable."
            )
        return ReportPayload(
            batch.identity,
            scope,
            MappingProxyType(dict(calculated.metrics)),
            calculated.series,
            detection,
            datetime.now(UTC).isoformat(timespec="seconds"),
        )

    def export_management_reports(self, scope: KpiScope) -> ReportArtifacts:
        """Render Excel and PDF from the same verified analytics payload."""
        payload = self.get_report_payload(scope)
        excel = pdf = None
        excel_error = pdf_error = None
        try:
            excel = render_excel(payload)
        except (OSError, ValueError, LayoutError):
            excel_error = "Excel generation failed for this selection."
        try:
            pdf = render_pdf(payload)
        except (OSError, ValueError, LayoutError):
            pdf_error = "PDF generation failed for this selection."
        if excel is None and pdf is None:
            raise ApplicationServiceError("Could not generate either management report format.")
        return ReportArtifacts(payload.identity, scope, excel, pdf, excel_error, pdf_error)

    def get_management_summary(
        self, scope: KpiScope, *, provider: Provider = openai_responses_provider
    ) -> ManagementSummary:
        """Generate a requested narrative from one coherent set of calculated facts."""
        payload = self.get_report_payload(scope)
        settings = Settings.from_environment()
        return generate_management_summary(
            payload,
            enabled=settings.ai_enabled,
            api_key=os.getenv("MOI_AI_API_KEY"),
            model=os.getenv("MOI_AI_MODEL", "gpt-4.1-mini"),
            provider=provider,
        )

    def _metrics(self, scope: KpiScope, keys: tuple[str, ...]) -> MetricsAnalysis:
        batch = self._load_batch()
        if batch is None:
            return MetricsAnalysis("no_active_batch", scope, None, {})
        calculated = calculate_dashboard_data(batch, scope)
        return MetricsAnalysis(
            "available",
            scope,
            batch.identity,
            {key: calculated.metrics[key] for key in keys},
            calculated.series,
        )

    def _load_batch(self):
        try:
            return self._repository.load_batch()
        except (RepositoryError, sqlite3.DatabaseError, OSError) as exc:
            raise ApplicationServiceError(
                "The active data could not be read. Check the local database and retry."
            ) from exc
