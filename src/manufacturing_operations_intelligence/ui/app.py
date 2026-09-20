"""Five plain-language Streamlit areas backed exclusively by application services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

import plotly.graph_objects as go
import streamlit as st

from manufacturing_operations_intelligence.services.application import (
    MAX_UPLOAD_BYTES,
    ApplicationServiceError,
    KpiScope,
    ManufacturingApplicationService,
    UploadProcessingResult,
)
from manufacturing_operations_intelligence.settings import Settings

_DATASETS = ("production_plan", "production_actual", "quality", "inventory")
_AREAS = ("Overview", "Production", "Quality", "Inventory", "Reports & Insights")
_BLUE = "#2563eb"
_TEAL = "#0f766e"
_AMBER = "#d97706"


def _feedback(result: UploadProcessingResult) -> None:
    if result.status == "accepted":
        if result.persistence is not None and result.persistence.status == "unchanged":
            st.success("These records are already active. Your dashboard data has not changed.")
        else:
            st.success("Data is ready. The dashboard now uses the validated upload.")
    elif result.status == "persistence_failed":
        st.error(
            "The files passed validation but could not be saved. No new data was activated. "
            "Check that local storage is available and writable, then retry."
        )
    else:
        st.error(
            "Upload not activated. Correct the source files using the details below, "
            "then upload all four datasets again. Any previously active data is unchanged."
        )
    validation = result.validation
    st.caption(
        f"Rows checked: {validation.evaluated_rows:,} · "
        f"Blocking issues: {validation.error_count:,} · "
        f"Rows with issues: {validation.affected_row_count:,} · "
        f"Format normalizations: {validation.normalization_action_count:,}"
    )
    if validation.unevaluated_rows is None:
        st.warning("Some source content could not be read; the unchecked row count is unknown.")
    elif validation.unevaluated_rows:
        st.warning(f"{validation.unevaluated_rows:,} source rows were not checked.")
    errors = [issue for issue in result.validation.issues if issue.severity == "ERROR"]
    if errors:
        with st.expander("Issues to correct in the source files", expanded=True):
            _validation_table(errors)
    changes = [issue for issue in result.validation.issues if issue.severity == "INFO"]
    if changes:
        with st.expander(f"Review format normalizations ({len(changes):,})"):
            st.caption(
                "These are permitted format conversions, not corrected business values. "
                "They apply to active data only when the upload is accepted."
            )
            page = st.number_input(
                "Normalization detail page",
                min_value=1,
                max_value=(len(changes) + 99) // 100,
                value=1,
                step=1,
                key=f"normalizations_{validation.attempt_id}",
            )
            start = (page - 1) * 100
            st.caption(
                f"Showing {start + 1:,}–{min(start + 100, len(changes)):,} of {len(changes):,}"
            )
            _validation_table(changes[start : start + 100])


def _validation_table(issues) -> None:
    st.dataframe(
        [
            {
                "Dataset": issue.dataset or "Upload",
                "File": issue.filename or "",
                "Sheet": issue.sheet or "",
                "Row": issue.row,
                "Field": issue.field or "",
                "Severity": issue.severity,
                "What happened": issue.reason,
                "Original value": issue.original,
                "Normalized value": issue.normalized,
                "How to fix it": issue.correction or "",
                "Related dataset": issue.counterpart_dataset or "",
                "Related file": issue.counterpart_filename or "",
                "Related rows": ", ".join(str(row) for row in issue.counterpart_rows),
                "Rule": issue.code,
            }
            for issue in issues
        ],
        hide_index=True,
        width="stretch",
    )


def _metric(result, label: str, help_text: str | None = None) -> None:
    value = result.display_value if result.status == "valid" else "N/A"
    st.metric(label, value or "N/A", help=help_text)
    if result.status != "valid":
        st.caption(result.reason or result.status.replace("_", " ").capitalize())


def _chart(title: str, traces: list[go.BaseTraceType], *, y_title: str) -> None:
    figure = go.Figure(data=traces)
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=330,
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text="",
        xaxis_title="",
        yaxis_title=y_title,
        hovermode="x unified",
    )
    st.plotly_chart(figure, width="stretch")


def _production_trend(series, *, title: str) -> None:
    if not series.daily:
        st.info("No production records match the selected dates, line, shift and product.")
        return
    days = [point.group for point in series.daily]
    _chart(
        title,
        [
            go.Scatter(
                x=days,
                y=[point.planned_qty for point in series.daily],
                name="Planned output",
                mode="lines",
                line=dict(color=_BLUE),
            ),
            go.Scatter(
                x=days,
                y=[point.actual_qty for point in series.daily],
                name="Actual output",
                mode="lines",
                line=dict(color=_TEAL),
            ),
        ],
        y_title="Finished pieces (ea)",
    )


def _production_lines(series) -> None:
    if not series.by_line:
        return
    lines = [point.group for point in series.by_line]
    _chart(
        "Output by production line",
        [
            go.Bar(
                x=lines,
                y=[point.planned_qty for point in series.by_line],
                name="Planned",
                marker_color=_BLUE,
            ),
            go.Bar(
                x=lines,
                y=[point.actual_qty for point in series.by_line],
                name="Actual",
                marker_color=_TEAL,
            ),
        ],
        y_title="Finished pieces (ea)",
    )


def _quality_trend(series) -> None:
    if not series.daily:
        st.info("No quality records match the selected production scope.")
        return
    days = [point.group for point in series.daily]
    _chart(
        "Final quality disposition by day",
        [
            go.Bar(
                x=days,
                y=[point.good_qty for point in series.daily],
                name="Good",
                marker_color=_TEAL,
            ),
            go.Bar(
                x=days,
                y=[point.scrap_qty for point in series.daily],
                name="Scrap",
                marker_color=_AMBER,
            ),
        ],
        y_title="Finished pieces (ea)",
    )
    st.caption("Good plus scrap equals actual output. Scrap means final scrap disposition.")


def _quality_lines(series) -> None:
    if not series.by_line:
        return
    _chart(
        "Final quality disposition by production line",
        [
            go.Bar(
                x=[point.group for point in series.by_line],
                y=[point.good_qty for point in series.by_line],
                name="Good",
                marker_color=_TEAL,
            ),
            go.Bar(
                x=[point.group for point in series.by_line],
                y=[point.scrap_qty for point in series.by_line],
                name="Scrap",
                marker_color=_AMBER,
            ),
        ],
        y_title="Finished pieces (ea)",
    )


def _downtime_by_line(series) -> None:
    if not series.by_line:
        return
    _chart(
        "Recorded downtime by production line",
        [
            go.Bar(
                x=[point.group for point in series.by_line],
                y=[float(point.downtime_minutes) for point in series.by_line],
                marker_color=_AMBER,
                name="Downtime",
            )
        ],
        y_title="Line-minutes",
    )


def _anomaly_panel(analysis, expected_batch_id: str, *, full: bool) -> None:
    if analysis.identity is not None and analysis.identity.batch_id != expected_batch_id:
        st.warning("The active data changed. Refresh the page to review current alerts.")
        return
    if analysis.status == "rules_not_configured":
        st.warning(
            "Alerts have not been checked. Enter a valid downtime threshold in the sidebar "
            "to enable anomaly checks. An empty alert list does not mean operations are normal."
        )
        return
    detection = analysis.detection
    if detection is None:
        st.info("No active dataset is available for alerts.")
        return
    if detection.status in {"invalid_data", "unsupported_schema"}:
        st.error("Alerts could not be checked. " + (detection.reason or "The data is unsupported."))
        return
    if detection.status == "no_data" or detection.evaluated_count == 0:
        st.warning("No alert checks completed for this scope. This is not an all-clear result.")
    elif detection.status == "partial_coverage" or detection.skipped_count:
        st.warning("Alert coverage is incomplete. Missing checks may hide operational issues.")
    if detection.reason:
        st.caption(detection.reason)
    if detection.anomaly_count:
        st.warning(f"{detection.anomaly_count} operational alerts need review.")
    elif (
        detection.status == "valid"
        and detection.evaluated_count > 0
        and not detection.skipped_count
    ):
        st.success("No rules triggered in the completed checks for this scope.")
    else:
        st.info("No alerts were detected in the available checks; coverage is incomplete.")
    st.caption(
        f"Completed checks: {detection.evaluated_count:,} · "
        f"Skipped checks: {detection.skipped_count:,}"
    )
    if detection.skipped_count:
        with st.expander("Why some checks were skipped"):
            st.dataframe(
                [
                    {
                        "Check": item.type.replace("_", " ").title(),
                        "Entity": item.entity.key,
                        "From": item.date_start,
                        "Through": item.date_end,
                        "Reason": item.reason,
                    }
                    for item in detection.skipped
                ],
                hide_index=True,
                width="stretch",
            )
    selected = detection.anomalies if full else detection.anomalies[:5]
    if selected:
        st.dataframe(
            [
                {
                    "Severity": item.severity,
                    "Alert": item.type.replace("_", " ").title(),
                    "Entity": item.entity.key,
                    "Date": item.date_start,
                    "What happened": item.explanation,
                    "Source evidence": "; ".join(
                        f"{ref.dataset} row {ref.source_row}" for ref in item.source_refs
                    ),
                }
                for item in selected
            ],
            hide_index=True,
            width="stretch",
        )
        if not full and detection.anomaly_count > len(selected):
            st.caption("Open Reports & Insights to review every alert.")


def _inventory_table(result) -> None:
    if result.status == "partial_coverage":
        st.warning(result.reason)
    if result.status == "no_data":
        st.info(result.reason or "No materials are available for this date.")
        return
    if not result.details:
        return
    st.dataframe(
        [
            {
                "Material": item["material_id"],
                "On hand": item.get("inventory_qty"),
                "Safety stock": item.get("safety_stock"),
                "Unit": item.get("qty_unit", ""),
                "Observed on": item.get("snapshot_date", ""),
                "Carried forward": item.get("carried_forward", False),
                "Below safety stock": item.get("below_safety_stock", ""),
                "Coverage": item["status"].replace("_", " "),
            }
            for item in result.details
        ],
        hide_index=True,
        width="stretch",
    )


def _series_table(series, *, title: str, source_refs) -> None:
    """Display service-prepared daily evidence without recalculating any KPI."""
    st.subheader(title)
    if series.daily:
        st.dataframe(
            [
                {
                    "Date": point.group,
                    "Planned (ea)": point.planned_qty,
                    "Actual (ea)": point.actual_qty,
                    "Good (ea)": point.good_qty,
                    "Scrap (ea)": point.scrap_qty,
                    "Downtime (line-minutes)": point.downtime_minutes,
                }
                for point in series.daily
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No selected production records are available for detail review.")
    if source_refs:
        with st.expander(f"Source evidence ({len(source_refs):,} rows)"):
            st.dataframe(
                [
                    {
                        "Dataset": ref.dataset,
                        "Source ID": ref.source_id,
                        "Source row": ref.source_row,
                    }
                    for ref in source_refs
                ],
                hide_index=True,
                width="stretch",
            )


def _upload_preview_rows(files, workbook) -> list[dict[str, object]]:
    """Present selected upload metadata before validation or activation."""
    if workbook is not None:
        return [
            {
                "Selected file": workbook.name,
                "Size (bytes)": workbook.size,
                "Domain assignment / expected sheets": ", ".join(_DATASETS),
            }
        ]
    return [
        {
            "Selected file": file.name if file is not None else "Not selected",
            "Size (bytes)": file.size if file is not None else None,
            "Domain assignment / expected sheets": dataset,
        }
        for dataset, file in files.items()
    ]


def _replacement_acknowledged(active_batch_id: str | None, action: str) -> bool:
    if active_batch_id is None:
        return True
    st.caption(
        "Activation replaces all four datasets currently used by the dashboard; "
        "it does not add records to them. Invalid uploads leave active data unchanged."
    )
    feedback = st.session_state.get("upload_feedback")
    attempt = feedback.validation.attempt_id if feedback is not None else "initial"
    return st.checkbox(
        f"I understand that {action} replaces the current dashboard data",
        key=f"replace_{action}_{active_batch_id}_{attempt}",
    )


def _upload_controls(service: ManufacturingApplicationService, active_batch_id: str | None) -> None:
    with st.sidebar.expander("Upload your own data"):
        upload_format = st.radio("File format", ("Four CSV files", "One Excel workbook"))
        if upload_format == "Four CSV files":
            files = {
                dataset: st.file_uploader(
                    dataset.replace("_", " ").title(), type="csv", key=f"upload_{dataset}"
                )
                for dataset in _DATASETS
            }
            workbook = None
        else:
            files = {}
            workbook = st.file_uploader("Workbook with four named sheets", type="xlsx")
        st.caption(
            "Batch preview — validation and activation do not occur until the button is used."
        )
        st.dataframe(_upload_preview_rows(files, workbook), hide_index=True, width="stretch")
        acknowledged = _replacement_acknowledged(active_batch_id, "this upload")
        if st.button("Validate and activate upload", disabled=not acknowledged) and acknowledged:
            if upload_format == "Four CSV files":
                if sum(file.size for file in files.values() if file is not None) > MAX_UPLOAD_BYTES:
                    st.error("The four CSV files exceed the 10,000,000-byte batch limit.")
                    return
                result = service.process_uploaded_data(
                    csv_files={
                        dataset: (file.name, file.getvalue())
                        for dataset, file in files.items()
                        if file is not None
                    }
                )
            elif workbook is not None:
                if workbook.size > MAX_UPLOAD_BYTES:
                    st.error("The workbook exceeds the 10,000,000-byte file limit.")
                    return
                result = service.process_uploaded_data(
                    workbook=(workbook.name, workbook.getvalue())
                )
            else:
                st.warning("Choose an Excel workbook first.")
                return
            st.session_state["upload_feedback"] = result
            st.rerun()


def main(settings: Settings | None = None) -> None:
    """Render the dashboard while services own validation, storage and analytics."""
    st.set_page_config(page_title="Manufacturing Operations Intelligence", layout="wide")
    st.title("Manufacturing Operations Intelligence")
    st.caption("One validated manufacturing dataset · local portfolio demonstration")
    try:
        current = settings or Settings.from_environment()
    except ValueError as exc:
        st.error(f"Configuration error: {exc}")
        return
    try:
        service = ManufacturingApplicationService.from_path(current.database_path)
        options = service.get_filter_options()
    except ApplicationServiceError as exc:
        st.error(str(exc))
        return

    if current.public_demo and options is None:
        try:
            result = service.load_sample_data()
            if result.status not in {"accepted", "unchanged"}:
                st.error("The public synthetic demo data could not be activated.")
                return
            options = service.get_filter_options()
        except ApplicationServiceError as exc:
            st.error(str(exc))
            return

    active_batch_id = options.identity.batch_id if options else None

    with st.sidebar:
        st.header("Get started")
        demo_requested = False
        if current.public_demo:
            st.caption("Public demo mode · synthetic data only · uploads are disabled.")
        else:
            acknowledged = _replacement_acknowledged(active_batch_id, "loading demo data")
            demo_requested = (
                st.button("Load synthetic demo data", disabled=not acknowledged) and acknowledged
            )
            if demo_requested:
                st.session_state["downtime_threshold"] = "120"
        threshold_text = st.text_input(
            "Downtime alert threshold (line-minutes per slot)",
            key="downtime_threshold",
            help="Use your site's rule. The synthetic demo uses 120 line-minutes.",
        )
        try:
            threshold = Decimal(threshold_text) if threshold_text.strip() else None
            service = ManufacturingApplicationService.from_path(
                current.database_path, downtime_above_minutes=threshold
            )
        except (InvalidOperation, ValueError):
            st.error(
                "Enter a finite number of zero or more, such as 120. "
                "Anomaly checks remain off until the threshold is valid."
            )
            service = ManufacturingApplicationService.from_path(current.database_path)
        if demo_requested:
            try:
                st.session_state["upload_feedback"] = service.load_sample_data()
                st.rerun()
            except ApplicationServiceError as exc:
                st.error(str(exc))
        if not current.public_demo:
            _upload_controls(service, active_batch_id)

    if "upload_feedback" in st.session_state:
        _feedback(st.session_state["upload_feedback"])

    try:
        options = service.get_filter_options()
    except ApplicationServiceError as exc:
        st.error(str(exc))
        return
    if options is None:
        st.info("Load the synthetic demo or upload all four manufacturing datasets to begin.")
        return

    with st.sidebar:
        st.header("View filters")
        start = st.date_input(
            "From", date.fromisoformat(options.start_date), key=f"start_{options.identity.batch_id}"
        )
        end = st.date_input(
            "Through", date.fromisoformat(options.end_date), key=f"end_{options.identity.batch_id}"
        )
        selected_lines = st.multiselect(
            "Production lines (blank means all)",
            options.line_ids,
            key=f"lines_{options.identity.batch_id}",
        )
        selected_shifts = st.multiselect(
            "Production shifts (blank means all)",
            options.shift_ids,
            key=f"shifts_{options.identity.batch_id}",
        )
        selected_products = st.multiselect(
            "Finished products (blank means all)",
            options.product_ids,
            key=f"products_{options.identity.batch_id}",
        )
        area = st.radio("Area", _AREAS)
        selected_materials = (
            st.multiselect(
                "Inventory materials (this page only; blank means all)",
                options.material_ids,
                key=f"materials_{options.identity.batch_id}",
            )
            if area == "Inventory"
            else ()
        )
    try:
        scope = KpiScope(
            start.isoformat(),
            end.isoformat(),
            line_ids=tuple(selected_lines) or None,
            shift_ids=tuple(selected_shifts) or None,
            product_ids=tuple(selected_products) or None,
            material_ids=(tuple(selected_materials) or None) if area == "Inventory" else None,
        )
    except ValueError:
        st.error("The start date must be on or before the end date.")
        return

    st.caption(
        f"Viewing {scope.start_date} through {scope.end_date} · "
        f"Batch {options.identity.batch_id[:8]}"
    )
    if area == "Overview":
        st.header("Overview")
        analysis = service.get_overview_metrics(scope)
        metrics = analysis.metrics
        first = st.columns(3)
        for column, key, label in zip(
            first,
            ("KPI-PA", "KPI-GY", "KPI-SR"),
            ("Production attainment", "Good yield", "Scrap rate"),
            strict=True,
        ):
            with column:
                _metric(metrics[key], label)
        second = st.columns(3)
        for column, key, label in zip(
            second,
            ("KPI-TD", "KPI-CO", "KPI-IR"),
            ("Total downtime", "Completed orders", "Materials below safety stock"),
            strict=True,
        ):
            with column:
                _metric(metrics[key], label)
        st.caption(
            "Inventory uses the latest material snapshot by the end date. "
            "Line and product filters affect production and quality only."
        )
        st.subheader("Alerts")
        _anomaly_panel(service.get_anomalies(scope), analysis.identity.batch_id, full=False)
        st.subheader("Production trend")
        _production_trend(analysis.series, title="Planned and actual output by day")
    elif area == "Production":
        st.header("Production")
        analysis = service.get_production_analysis(scope)
        cols = st.columns(2)
        with cols[0]:
            _metric(analysis.metrics["KPI-PA"], "Production attainment")
        with cols[1]:
            _metric(analysis.metrics["KPI-TD"], "Total downtime")
        _production_trend(analysis.series, title="Planned and actual output by day")
        _production_lines(analysis.series)
        _downtime_by_line(analysis.series)
        _series_table(
            analysis.series,
            title="Selected production detail",
            source_refs=analysis.metrics["KPI-PA"].source_refs,
        )
        st.subheader("Relevant operational alerts")
        _anomaly_panel(service.get_anomalies(scope), analysis.identity.batch_id, full=True)
    elif area == "Quality":
        st.header("Quality")
        analysis = service.get_quality_analysis(scope)
        cols = st.columns(3)
        with cols[0]:
            _metric(analysis.metrics["KPI-GY"], "Good yield")
        with cols[1]:
            _metric(analysis.metrics["KPI-SR"], "Scrap rate")
        with cols[2]:
            produced = analysis.metrics["KPI-GY"].denominator
            st.metric("Produced output", f"{produced:,} ea" if produced is not None else "N/A")
        _quality_trend(analysis.series)
        _quality_lines(analysis.series)
        _series_table(
            analysis.series,
            title="Selected quality detail",
            source_refs=analysis.metrics["KPI-GY"].source_refs,
        )
        st.subheader("Relevant operational alerts")
        _anomaly_panel(service.get_anomalies(scope), analysis.identity.batch_id, full=True)
    elif area == "Inventory":
        st.header("Inventory")
        st.caption(
            "As of the selected end date; line, shift and product filters do not apply. "
            "The material selector affects this page only, never full reports."
        )
        analysis = service.get_inventory_analysis(scope)
        risk = analysis.metrics["KPI-IR"]
        _metric(risk, "Materials below safety stock")
        _inventory_table(risk)
        if risk.coverage:
            _chart(
                "Stock observations needing review",
                [
                    go.Bar(
                        x=["Below safety stock", "No eligible snapshot"],
                        y=[
                            risk.coverage.get("observed_at_risk", 0),
                            risk.coverage.get("missing_materials", 0),
                        ],
                        marker_color=[_AMBER, _BLUE],
                    )
                ],
                y_title="Materials",
            )
    else:
        st.header("Reports & Insights")
        st.caption(
            "This view uses the current batch and filters. Inventory is site-wide "
            "as of the end date."
        )
        analysis = service.get_overview_metrics(scope)
        st.subheader("Report scope preview")
        st.write(
            f"Batch {analysis.identity.batch_id[:8]} · {scope.start_date} through {scope.end_date}"
        )
        _production_trend(analysis.series, title="Production trend in this scope")
        st.subheader("All detected anomalies")
        anomaly_analysis = service.get_anomalies(scope)
        _anomaly_panel(anomaly_analysis, analysis.identity.batch_id, full=True)
        report_key = (
            options.identity.batch_id,
            options.identity.fingerprint,
            options.identity.contract_version,
            analysis.metrics["KPI-PA"].definition_version,
            anomaly_analysis.detection.rule_version if anomaly_analysis.detection else None,
            scope,
            threshold_text,
        )
        st.subheader("Management summary")
        st.caption(
            "Generate a factual offline summary, or an optional AI draft when configured. "
            "AI drafts need human review; charts and reports remain available without AI."
        )
        prepared_summary = st.session_state.get("prepared_summary")
        if prepared_summary is not None and prepared_summary[0] != report_key:
            st.session_state.pop("prepared_summary", None)
            prepared_summary = None
        if st.button("Generate management summary"):
            st.session_state.pop("prepared_summary", None)
            prepared_summary = None
            try:
                summary = service.get_management_summary(scope)
                if summary.identity.batch_id != options.identity.batch_id:
                    st.warning("The active data changed. Refresh the page and try again.")
                else:
                    st.session_state["prepared_summary"] = (report_key, summary)
                    st.session_state.pop("prepared_report", None)
                    prepared_summary = (report_key, summary)
            except ApplicationServiceError as exc:
                st.error(str(exc))
        if prepared_summary is not None:
            summary = prepared_summary[1]
            if summary.status == "ai_draft":
                st.info("AI-assisted draft · Review all statements before use.")
            else:
                reasons = {
                    "fallback_disabled": "AI is disabled.",
                    "fallback_missing_key": "No AI API key is configured.",
                    "fallback_timeout": "The AI request timed out.",
                    "fallback_api_failure": "The AI service is unavailable.",
                    "fallback_malformed": "The AI response could not be used.",
                    "fallback_unsupported_claim": (
                        "The AI response referenced an unsupported fact."
                    ),
                }
                st.info(f"Deterministic offline summary · {reasons[summary.status]}")
            for heading, lines in (
                ("Observations", summary.observations),
                ("Management attention", summary.management_attention),
                ("Limitations", summary.limitations),
            ):
                st.markdown(f"**{heading}**")
                for line in lines:
                    st.write(line)
        prepared = st.session_state.get("prepared_report")
        if prepared is not None and prepared[0] != report_key:
            st.session_state.pop("prepared_report", None)
            prepared = None
        if st.button("Generate management reports"):
            st.session_state.pop("prepared_report", None)
            prepared = None
            try:
                artifact = service.export_management_reports(
                    scope,
                    summary=prepared_summary[1] if prepared_summary is not None else None,
                )
                if artifact.identity.batch_id != options.identity.batch_id:
                    st.warning(
                        "The active data changed. Refresh the page and generate reports again."
                    )
                else:
                    st.session_state["prepared_report"] = (report_key, artifact)
                    prepared = (report_key, artifact)
            except ApplicationServiceError as exc:
                st.error(str(exc))
        if prepared is not None:
            artifact = prepared[1]
            stem = f"manufacturing-report-{scope.start_date}-to-{scope.end_date}"
            st.success("Available reports are ready for the current batch and filters.")
            if artifact.excel is not None:
                st.download_button(
                    "Download Excel report",
                    artifact.excel,
                    file_name=f"{stem}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            if artifact.pdf is not None:
                st.download_button(
                    "Download PDF report",
                    artifact.pdf,
                    file_name=f"{stem}.pdf",
                    mime="application/pdf",
                )
            for issue in (artifact.excel_error, artifact.pdf_error):
                if issue:
                    st.warning(issue)
