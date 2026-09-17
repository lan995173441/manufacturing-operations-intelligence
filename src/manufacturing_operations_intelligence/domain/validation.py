"""Data Contract validation independent of UI and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Literal
from uuid import uuid4

from manufacturing_operations_intelligence.domain.normalization import (
    InvalidValue,
    is_missing,
    normalize,
)

COMMON = {
    "production_date": "DATE",
    "line_id": "ID",
    "shift_id": "ID",
    "order_id": "ID",
    "product_id": "ID",
    "qty_unit": "UNIT",
}
SCHEMAS = {
    "production_plan": {**COMMON, "planned_qty": "COUNT", "planned_production_minutes": "MINUTES"},
    "production_actual": {
        **COMMON,
        "actual_qty": "COUNT",
        "runtime_minutes": "MINUTES",
        "downtime_minutes": "MINUTES",
    },
    "quality": {**COMMON, "good_qty": "COUNT", "scrap_qty": "COUNT"},
    "inventory": {
        "snapshot_date": "DATE",
        "material_id": "ID",
        "qty_unit": "UNIT",
        "inventory_qty": "STOCK",
        "safety_stock": "STOCK",
    },
}
ALIASES = {
    "production_plan": {
        "date": "production_date",
        "planned_units": "planned_qty",
        "planned_minutes": "planned_production_minutes",
    },
    "production_actual": {
        "date": "production_date",
        "produced_units": "actual_qty",
        "unplanned_downtime_minutes": "downtime_minutes",
    },
    "quality": {"date": "production_date"},
    "inventory": {"on_hand_qty": "inventory_qty", "minimum_qty": "safety_stock"},
}
PRODUCTION_KEY = ("production_date", "line_id", "shift_id")
INVENTORY_KEY = ("snapshot_date", "material_id")


@dataclass(frozen=True)
class ValidationIssue:
    dataset: str | None
    row: int | None
    field: str | None
    reason: str
    severity: Literal["ERROR", "INFO"]
    code: str
    source_id: str | None = None
    filename: str | None = None
    sheet: str | None = None
    original: str | None = None
    correction: str | None = None
    counterpart_rows: tuple[int, ...] = ()
    counterpart_dataset: str | None = None
    counterpart_filename: str | None = None
    normalized: str | None = None


@dataclass(frozen=True)
class ValidatedRow:
    source_id: str
    source_row: int
    values: dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    attempt_id: str
    accepted: bool
    status: Literal["accepted", "rejected"]
    stage: str
    issues: tuple[ValidationIssue, ...]
    candidates: dict[str, tuple[ValidatedRow, ...]]
    records: dict[str, tuple[ValidatedRow, ...]]
    total_observed_rows: int | None
    evaluated_rows: int
    unevaluated_rows: int | None
    error_count: int
    affected_row_count: int
    normalization_action_count: int
    sources: tuple[Any, ...]


@dataclass
class _State:
    issues: list[ValidationIssue] = field(default_factory=list)
    candidates: dict[str, list[ValidatedRow]] = field(
        default_factory=lambda: {name: [] for name in SCHEMAS}
    )

    def issue(
        self,
        source: Any | None,
        code: str,
        reason: str,
        *,
        row: int | None = None,
        field_name: str | None = None,
        severity: Literal["ERROR", "INFO"] = "ERROR",
        original: Any = None,
        normalized: Any = None,
        correction: str | None = None,
        counterpart_rows: tuple[int, ...] = (),
        counterpart_source: Any | None = None,
        dataset: str | None = None,
        filename: str | None = None,
        sheet: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                source.dataset if source else dataset,
                row,
                field_name,
                reason,
                severity,
                f"DATA.{code}",
                source.source_id if source else None,
                source.filename if source else filename,
                source.sheet if source else sheet,
                _safe(original),
                correction,
                counterpart_rows,
                counterpart_source.dataset if counterpart_source else None,
                counterpart_source.filename if counterpart_source else None,
                _safe(normalized),
            )
        )


def _safe(value: Any) -> str | None:
    if value is None:
        return None
    representation = str(value)
    return representation[:100] + ("…" if len(representation) > 100 else "")


def _canonical_header(value: Any, dataset: str) -> str | None:
    if not isinstance(value, str):
        return None
    header = value.strip().translate(
        str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
    )
    return ALIASES[dataset].get(header, header)


def _validate_source(state: _State, source: Any) -> None:
    dataset = source.dataset
    if dataset not in SCHEMAS:
        state.issue(source, "E-PACKAGE", "Unknown dataset assignment.")
        return
    schema = SCHEMAS[dataset]
    if source.had_bom:
        state.issue(
            source,
            "N01",
            "UTF-8 BOM removed before header parsing.",
            original="UTF-8 BOM",
            normalized="UTF-8",
            severity="INFO",
        )
    indices: dict[str, int] = {}
    for index, original in enumerate(source.headers):
        canonical = _canonical_header(original, dataset)
        if canonical is None or canonical not in schema:
            state.issue(
                source,
                "E-SCHEMA",
                "Unexpected or invalid header.",
                field_name=_safe(original),
                original=original,
                correction="Use a documented canonical header or alias.",
            )
        elif canonical in indices:
            state.issue(
                source,
                "E-SCHEMA",
                f"Duplicate normalized header: {canonical}.",
                field_name=canonical,
                original=original,
                correction="Keep exactly one column for this field.",
            )
        else:
            indices[canonical] = index
            if canonical != original:
                state.issue(
                    source,
                    "N02",
                    "Header normalized.",
                    field_name=canonical,
                    original=original,
                    normalized=canonical,
                    severity="INFO",
                )
    for required in schema:
        if required not in indices:
            state.issue(
                source,
                "E-SCHEMA",
                "Required column is missing.",
                field_name=required,
                correction="Add the required column with source values.",
            )

    for raw in source.rows:
        if len(raw.values) != len(source.headers):
            continue
        values: dict[str, Any] = {}
        invalid = False
        for name, kind in schema.items():
            if name not in indices:
                invalid = True
                continue
            original = raw.values[indices[name]]
            if is_missing(original):
                state.issue(
                    source,
                    "E-MISSING",
                    "Required value is missing.",
                    row=raw.row,
                    field_name=name,
                    original=original,
                    correction="Supply a valid source value; do not substitute zero for missing.",
                )
                invalid = True
                continue
            try:
                unit = values.get("qty_unit") if kind == "STOCK" else dataset
                clean = normalize(original, kind, excel=source.kind == "xlsx", unit=unit)
            except InvalidValue as exc:
                state.issue(
                    source,
                    f"T-{kind}",
                    str(exc),
                    row=raw.row,
                    field_name=name,
                    original=original,
                    correction="Correct this source value.",
                )
                invalid = True
                continue
            values[name] = clean
            if str(original) != str(clean) or type(original) is not type(clean):
                action = {
                    "ID": "N03",
                    "DATE": "N04",
                    "COUNT": "N05",
                    "MINUTES": "N06",
                    "STOCK": "N06",
                    "UNIT": "N07",
                }[kind]
                state.issue(
                    source,
                    action,
                    "Value normalized.",
                    row=raw.row,
                    field_name=name,
                    original=original,
                    normalized=clean,
                    severity="INFO",
                )
        if not invalid:
            state.candidates[dataset].append(ValidatedRow(source.source_id, raw.row, values))


def _integrity(state: _State, source_by_dataset: dict[str, Any]) -> None:
    indices: dict[str, dict[tuple[Any, ...], ValidatedRow]] = {}
    for dataset, rows in state.candidates.items():
        source = source_by_dataset.get(dataset)
        keys: dict[tuple[Any, ...], list[ValidatedRow]] = {}
        key_fields = INVENTORY_KEY if dataset == "inventory" else PRODUCTION_KEY
        for record in rows:
            key = tuple(record.values[name] for name in key_fields)
            keys.setdefault(key, []).append(record)
        for duplicates in keys.values():
            if len(duplicates) > 1:
                for record in duplicates:
                    state.issue(
                        source,
                        "R01",
                        "Duplicate business key after normalization.",
                        row=record.source_row,
                        field_name=", ".join(key_fields),
                        counterpart_rows=tuple(
                            other.source_row for other in duplicates if other is not record
                        ),
                        correction="Remove or correct every duplicate source row.",
                    )
        indices[dataset] = {key: records[0] for key, records in keys.items()}

    for dataset in ("production_plan", "production_actual", "quality"):
        source = source_by_dataset.get(dataset)
        if not source:
            continue
        for key, record in indices[dataset].items():
            for other_dataset in ("production_plan", "production_actual", "quality"):
                if other_dataset == dataset or other_dataset not in source_by_dataset:
                    continue
                other = indices[other_dataset].get(key)
                if other is None:
                    state.issue(
                        source,
                        "R02",
                        f"No matching {other_dataset} slot.",
                        row=record.source_row,
                        field_name=", ".join(PRODUCTION_KEY),
                        correction=f"Provide a matching {other_dataset} record.",
                    )
                elif dataset == "production_plan":
                    for name in ("order_id", "product_id", "qty_unit"):
                        if record.values[name] != other.values[name]:
                            state.issue(
                                source,
                                "R03",
                                f"{name} disagrees with {other_dataset}.",
                                row=record.source_row,
                                field_name=name,
                                counterpart_rows=(other.source_row,),
                                counterpart_source=source_by_dataset[other_dataset],
                                correction="Make slot identifiers agree in all three datasets.",
                            )

    order_products: dict[str, tuple[str, ValidatedRow]] = {}
    for record in state.candidates["production_plan"]:
        order_id = record.values["order_id"]
        product_id = record.values["product_id"]
        previous = order_products.get(order_id)
        if previous and previous[0] != product_id:
            state.issue(
                source_by_dataset.get("production_plan"),
                "R03",
                "An order refers to multiple products.",
                row=record.source_row,
                field_name="product_id",
                counterpart_rows=(previous[1].source_row,),
                correction="Use one product per order within this batch.",
            )
        else:
            order_products[order_id] = (product_id, record)

    plan = indices["production_plan"]
    actual = indices["production_actual"]
    quality = indices["quality"]
    for key in plan.keys() & actual.keys():
        planned, produced = plan[key], actual[key]
        if (
            produced.values["runtime_minutes"] + produced.values["downtime_minutes"]
            > planned.values["planned_production_minutes"]
        ):
            state.issue(
                source_by_dataset.get("production_actual"),
                "R05",
                "Runtime plus downtime exceeds planned production minutes.",
                row=produced.source_row,
                field_name="runtime_minutes",
                counterpart_rows=(planned.source_row,),
                counterpart_source=source_by_dataset.get("production_plan"),
                correction="Correct the recorded time values.",
            )
    for key in actual.keys() & quality.keys():
        produced, inspected = actual[key], quality[key]
        if (
            inspected.values["good_qty"] + inspected.values["scrap_qty"]
            != produced.values["actual_qty"]
        ):
            state.issue(
                source_by_dataset.get("quality"),
                "R04",
                "Good plus scrap does not equal actual output.",
                row=inspected.source_row,
                field_name="good_qty, scrap_qty",
                counterpart_rows=(produced.source_row,),
                counterpart_source=source_by_dataset.get("production_actual"),
                correction="Correct the supplied disposition or output values.",
            )
    line_minutes: dict[tuple[str, str], Decimal] = {}
    line_rows: dict[tuple[str, str], list[int]] = {}
    for record in state.candidates["production_plan"]:
        key = (record.values["production_date"], record.values["line_id"])
        line_minutes[key] = (
            line_minutes.get(key, Decimal(0)) + record.values["planned_production_minutes"]
        )
        line_rows.setdefault(key, []).append(record.source_row)
    for key, total in line_minutes.items():
        if total > 1440:
            for row in line_rows[key]:
                state.issue(
                    source_by_dataset.get("production_plan"),
                    "R06",
                    "Daily planned line-minutes exceed 1440.",
                    row=row,
                    field_name="planned_production_minutes",
                    counterpart_rows=tuple(other for other in line_rows[key] if other != row),
                    correction="Correct planned windows for this line/date.",
                )
    material_units: dict[str, tuple[str, ValidatedRow]] = {}
    for record in state.candidates["inventory"]:
        material = record.values["material_id"]
        previous = material_units.get(material)
        if previous and previous[0] != record.values["qty_unit"]:
            state.issue(
                source_by_dataset.get("inventory"),
                "R07",
                "Material unit changes within the batch.",
                row=record.source_row,
                field_name="qty_unit",
                counterpart_rows=(previous[1].source_row,),
                correction="Use one unit for each material.",
            )
        else:
            material_units[material] = (record.values["qty_unit"], record)


def validate_sources(
    sources: tuple[Any, ...],
    package_problems: tuple[Any, ...] = (),
    *,
    total_bytes: int | None = None,
) -> ValidationResult:
    """Validate a complete attempt; expose candidates but publish only an error-free batch."""
    state = _State()
    source_by_dataset = {source.dataset: source for source in sources}
    if total_bytes is not None and total_bytes > 10_000_000:
        state.issue(None, "E-LIMIT", "Total input exceeds 10,000,000 bytes.")
    for dataset in SCHEMAS.keys() - source_by_dataset.keys():
        state.issue(None, "E-PACKAGE", f"Missing source for {dataset}.", dataset=dataset)
    if len(sources) != len(source_by_dataset):
        state.issue(None, "E-PACKAGE", "A dataset was assigned more than once.")
    for problem in (*package_problems, *(p for source in sources for p in source.problems)):
        source = source_by_dataset.get(problem.dataset)
        state.issue(
            source,
            problem.code,
            problem.reason,
            row=problem.row,
            field_name=problem.field,
            correction=problem.correction,
            dataset=problem.dataset,
            filename=problem.filename,
            sheet=problem.sheet,
        )
    observed = sum(len(source.rows) for source in sources)
    if observed > 10_000:
        state.issue(None, "E-LIMIT", "Total data rows exceed 10,000.")
    for source in sources:
        if not source.rows:
            state.issue(source, "E-MISSING", "Dataset has no candidate records.")
        if source.dataset in SCHEMAS:
            _validate_source(state, source)
    _integrity(state, source_by_dataset)
    error_issues = [issue for issue in state.issues if issue.severity == "ERROR"]
    uncertain = any(source.total_rows is None for source in sources) or any(
        problem.code in {"E-PARSE", "E-LIMIT"} for problem in package_problems
    )
    total = None if uncertain else observed
    candidates = {name: tuple(rows) for name, rows in state.candidates.items()}
    accepted = not error_issues
    return ValidationResult(
        str(uuid4()),
        accepted,
        "accepted" if accepted else "rejected",
        "complete" if not uncertain else "parse_incomplete",
        tuple(state.issues),
        candidates,
        candidates if accepted else {name: () for name in SCHEMAS},
        total,
        observed,
        None if uncertain else 0,
        len(error_issues),
        len({(issue.dataset, issue.row) for issue in error_issues if issue.row is not None}),
        sum(issue.severity == "INFO" for issue in state.issues),
        sources,
    )


def validate_normalized_records(records: dict[str, tuple[Any, ...]]) -> tuple[ValidationIssue, ...]:
    """Check canonical persisted records without repairing them or performing I/O."""
    state = _State()
    sources = {}
    if set(records) != set(SCHEMAS):
        state.issue(None, "E-SCHEMA", "Expected exactly four canonical datasets.")
        return tuple(state.issues)
    for dataset, schema in SCHEMAS.items():
        rows = records[dataset]
        source = SimpleNamespace(
            dataset=dataset,
            source_id=rows[0].source_id if rows else None,
            filename=None,
            sheet=None,
        )
        sources[dataset] = source
        if not rows:
            state.issue(source, "E-MISSING", "Canonical dataset is empty.")
        for record in rows:
            valid = True
            if (
                not record.source_id
                or record.source_id != source.source_id
                or type(record.source_row) is not int
                or record.source_row < 2
            ):
                state.issue(source, "E-MISSING", "Record provenance is missing or invalid.")
                valid = False
            if set(record.values) != set(schema):
                state.issue(
                    source,
                    "E-SCHEMA",
                    "Canonical record fields do not match schema.",
                    row=record.source_row,
                )
                valid = False
            for name, kind in schema.items():
                value = record.values.get(name)
                try:
                    if is_missing(value):
                        raise InvalidValue("Required canonical value is missing.")
                    unit = record.values.get("qty_unit") if kind == "STOCK" else dataset
                    canonical = normalize(value, kind, excel=True, unit=unit)
                    if type(value) is not type(canonical) or value != canonical:
                        raise InvalidValue("Value is not canonical; analytics cannot normalize it.")
                except (InvalidValue, ArithmeticError) as exc:
                    state.issue(
                        source, f"T-{kind}", str(exc), row=record.source_row, field_name=name
                    )
                    valid = False
            if valid:
                state.candidates[dataset].append(
                    ValidatedRow(record.source_id, record.source_row, dict(record.values))
                )
    _integrity(state, sources)
    return tuple(state.issues)
