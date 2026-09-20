"""Environment-backed settings for the local application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


@dataclass(frozen=True, slots=True)
class Settings:
    """Small set of environment settings; no business configuration belongs here."""

    environment: str
    database_path: Path
    ai_enabled: bool
    public_demo: bool

    @classmethod
    def from_environment(cls) -> Settings:
        """Build settings from operating-system environment variables."""
        return cls(
            environment=os.getenv("MOI_ENVIRONMENT", "development"),
            database_path=Path(
                os.getenv(
                    "MOI_DATABASE_PATH",
                    "var/manufacturing_operations_intelligence.db",
                )
            ),
            ai_enabled=_read_bool("MOI_AI_ENABLED", default=False),
            public_demo=_read_bool("MOI_PUBLIC_DEMO", default=False),
        )
