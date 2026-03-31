"""Load and merge configuration from .specs/config/.

Reads settings.yaml, prefixes.yaml, schema.yaml, priority.yaml,
cycles.yaml, and hooks.yaml. Provides typed access via Pydantic
settings models.

Key class:
    DiatagmaConfig(specs_dir: Path)
        .settings   → Settings
        .prefixes   → dict[str, PrefixDef]
        .schema     → SchemaConfig
        .priority   → PriorityConfig
        .cycles     → list[Cycle]
        .hooks      → HooksConfig
        .templates  → dict[str, str]  (spec_type → template content)
"""

from __future__ import annotations

from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from diatagma.core.models import (
    HooksConfig,
    PrefixDef,
    PriorityConfig,
    SchemaConfig,
    Settings,
    Cycle,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised when a configuration file cannot be loaded or validated."""


# ---------------------------------------------------------------------------
# YAML loading helper
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict | list | None:
    """Read and parse a YAML file.

    Returns None if the file does not exist or is empty.
    Raises ConfigError on malformed YAML.
    """
    if not path.exists():
        logger.debug("config file not found: {}", path)
        return None

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Per-file loaders
# ---------------------------------------------------------------------------


def _load_settings(config_dir: Path) -> Settings:
    """Load settings.yaml, returning defaults if missing."""
    data = _load_yaml(config_dir / "settings.yaml")
    if data is None or not isinstance(data, dict):
        return Settings()
    try:
        return Settings.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"invalid settings.yaml: {exc}") from exc


def _load_prefixes(config_dir: Path) -> dict[str, PrefixDef]:
    """Load prefixes.yaml as {PREFIX: PrefixDef}."""
    data = _load_yaml(config_dir / "prefixes.yaml")
    if data is None or not isinstance(data, dict):
        return {}
    try:
        return {
            prefix: PrefixDef.model_validate(value) for prefix, value in data.items()
        }
    except ValidationError as exc:
        raise ConfigError(f"invalid prefixes.yaml: {exc}") from exc


def _load_schema(config_dir: Path) -> SchemaConfig:
    """Load schema.yaml, returning defaults if missing."""
    data = _load_yaml(config_dir / "schema.yaml")
    if data is None or not isinstance(data, dict):
        return SchemaConfig()
    try:
        return SchemaConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"invalid schema.yaml: {exc}") from exc


def _load_priority(config_dir: Path) -> PriorityConfig:
    """Load priority.yaml, returning defaults if missing."""
    data = _load_yaml(config_dir / "priority.yaml")
    if data is None or not isinstance(data, dict):
        return PriorityConfig()
    try:
        return PriorityConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"invalid priority.yaml: {exc}") from exc


def _load_cycles(config_dir: Path) -> list[Cycle]:
    """Load cycles.yaml, returning [] if missing or empty."""
    data = _load_yaml(config_dir / "cycles.yaml")
    if data is None or not isinstance(data, dict):
        return []
    raw_list = data.get("cycles")
    if not isinstance(raw_list, list):
        return []
    try:
        return [Cycle.model_validate(item) for item in raw_list]
    except ValidationError as exc:
        raise ConfigError(f"invalid cycles.yaml: {exc}") from exc


def _load_hooks(config_dir: Path) -> HooksConfig:
    """Load hooks.yaml, returning defaults if missing or empty."""
    data = _load_yaml(config_dir / "hooks.yaml")
    if data is None or not isinstance(data, dict):
        return HooksConfig()
    raw_hooks = data.get("hooks")
    if not isinstance(raw_hooks, dict):
        return HooksConfig()
    try:
        return HooksConfig.model_validate(raw_hooks)
    except ValidationError as exc:
        raise ConfigError(f"invalid hooks.yaml: {exc}") from exc


def _load_templates(config_dir: Path) -> dict[str, str]:
    """Load all .md files from config/templates/ as {name: content}."""
    templates_dir = config_dir / "templates"
    if not templates_dir.is_dir():
        return {}
    result: dict[str, str] = {}
    for path in sorted(templates_dir.glob("*.md")):
        result[path.stem] = path.read_text(encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# DiatagmaConfig
# ---------------------------------------------------------------------------


class DiatagmaConfig:
    """Top-level configuration container.

    Loads all YAML config files and templates from ``specs_dir/config/``
    eagerly on construction. Missing files produce defaults; malformed
    files raise ConfigError.
    """

    def __init__(self, specs_dir: Path) -> None:
        self._specs_dir = Path(specs_dir)
        config_dir = self._specs_dir / "config"

        self._settings = _load_settings(config_dir)
        self._prefixes = _load_prefixes(config_dir)
        self._schema = _load_schema(config_dir)
        self._priority = _load_priority(config_dir)
        self._cycles = _load_cycles(config_dir)
        self._hooks = _load_hooks(config_dir)
        self._templates = _load_templates(config_dir)

    @property
    def specs_dir(self) -> Path:
        return self._specs_dir

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def prefixes(self) -> dict[str, PrefixDef]:
        return self._prefixes

    @property
    def schema(self) -> SchemaConfig:
        return self._schema

    @property
    def priority(self) -> PriorityConfig:
        return self._priority

    @property
    def cycles(self) -> list[Cycle]:
        return self._cycles

    @property
    def hooks(self) -> HooksConfig:
        return self._hooks

    @property
    def templates(self) -> dict[str, str]:
        return self._templates


__all__ = [
    "ConfigError",
    "DiatagmaConfig",
]
