"""Foundation smoke tests."""

import tomllib
from importlib import import_module
from pathlib import Path

from manufacturing_operations_intelligence import __version__
from manufacturing_operations_intelligence.settings import Settings
from manufacturing_operations_intelligence.ui.app import main


def test_foundation_imports_and_defaults(monkeypatch) -> None:
    """The architecture boundaries and required dependencies import cleanly."""
    for variable in ("MOI_ENVIRONMENT", "MOI_DATABASE_PATH", "MOI_AI_ENABLED"):
        monkeypatch.delenv(variable, raising=False)

    modules = (
        "streamlit",
        "pandas",
        "plotly",
        "openpyxl",
        "reportlab",
        "manufacturing_operations_intelligence.services",
        "manufacturing_operations_intelligence.domain.validation",
        "manufacturing_operations_intelligence.domain.normalization",
        "manufacturing_operations_intelligence.domain.analytics",
        "manufacturing_operations_intelligence.data.readers",
        "manufacturing_operations_intelligence.data.repository",
        "manufacturing_operations_intelligence.reporting",
        "manufacturing_operations_intelligence.summaries",
    )
    for module in modules:
        assert import_module(module)

    settings = Settings.from_environment()
    assert __version__ == "1.0.0"
    project = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert project["project"]["version"] == __version__
    assert settings.environment == "development"
    assert settings.database_path == Path("var/manufacturing_operations_intelligence.db")
    assert settings.ai_enabled is False
    assert callable(main)
