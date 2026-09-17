"""Coordinate source decoding and pure validation without UI or persistence."""

from __future__ import annotations

from collections.abc import Mapping

from manufacturing_operations_intelligence.data.readers import (
    DATASETS,
    MAX_BYTES,
    ReadProblem,
    read_csv,
    read_workbook,
)
from manufacturing_operations_intelligence.domain.validation import (
    ValidationResult,
    validate_sources,
)


def ingest_csv_batch(files: Mapping[str, tuple[str, bytes]]) -> ValidationResult:
    """Validate four explicitly assigned CSV sources as one complete batch."""
    problems = []
    for dataset in files.keys() - set(DATASETS):
        problems.append(
            ReadProblem(
                dataset,
                None,
                None,
                "E-PACKAGE",
                "Unknown dataset.",
                "Assign one of the four canonical datasets.",
            )
        )
    total_bytes = sum(len(content) for _, content in files.values())
    if total_bytes > MAX_BYTES:
        return validate_sources(
            (),
            tuple(problems)
            + (
                ReadProblem(
                    None,
                    None,
                    None,
                    "E-LIMIT",
                    "Total input exceeds 10,000,000 bytes.",
                    "Reduce the batch size.",
                ),
            ),
            total_bytes=total_bytes,
        )
    sources = tuple(read_csv(dataset, *files[dataset]) for dataset in DATASETS if dataset in files)
    return validate_sources(sources, tuple(problems), total_bytes=total_bytes)


def ingest_excel_workbook(filename: str, content: bytes) -> ValidationResult:
    """Validate one workbook with exactly four canonical worksheets."""
    sources, problems = read_workbook(filename, content)
    return validate_sources(sources, problems, total_bytes=len(content))
