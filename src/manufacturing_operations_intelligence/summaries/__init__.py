"""Deterministic and optional AI summary-adapter boundary."""

from manufacturing_operations_intelligence.summaries.management import (
    ManagementSummary,
    Provider,
    generate_management_summary,
    openai_responses_provider,
    project_facts,
)

__all__ = [
    "ManagementSummary", "Provider", "generate_management_summary",
    "openai_responses_provider", "project_facts",
]
