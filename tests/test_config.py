"""Tests for core.config — YAML configuration loading."""

from datetime import date
from pathlib import Path

import pytest

from diatagma.core.config import (
    ConfigError,
    DiatagmaConfig,
    _load_hooks,
    _load_prefixes,
    _load_priority,
    _load_schema,
    _load_settings,
    _load_sprints,
    _load_templates,
    _load_yaml,
)
from diatagma.core.models import (
    HooksConfig,
    PrefixDef,
    PriorityConfig,
    SchemaConfig,
    Settings,
    Sprint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    """Write text to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# TestLoadYaml
# ---------------------------------------------------------------------------


class TestLoadYaml:
    """Tests for _load_yaml()."""

    def test_valid_file(self, tmp_path: Path) -> None:
        _write(tmp_path / "test.yaml", "key: value\n")
        result = _load_yaml(tmp_path / "test.yaml")
        assert result == {"key": "value"}

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _load_yaml(tmp_path / "nope.yaml") is None

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        _write(tmp_path / "empty.yaml", "")
        assert _load_yaml(tmp_path / "empty.yaml") is None

    def test_whitespace_only_returns_none(self, tmp_path: Path) -> None:
        _write(tmp_path / "blank.yaml", "   \n\n  ")
        assert _load_yaml(tmp_path / "blank.yaml") is None

    def test_malformed_yaml_raises_config_error(self, tmp_path: Path) -> None:
        _write(tmp_path / "bad.yaml", "key: [unclosed\n")
        with pytest.raises(ConfigError, match="invalid YAML"):
            _load_yaml(tmp_path / "bad.yaml")

    def test_comments_only_returns_none(self, tmp_path: Path) -> None:
        _write(tmp_path / "comments.yaml", "# just a comment\n# another\n")
        assert _load_yaml(tmp_path / "comments.yaml") is None

    def test_list_yaml(self, tmp_path: Path) -> None:
        _write(tmp_path / "list.yaml", "- one\n- two\n")
        result = _load_yaml(tmp_path / "list.yaml")
        assert result == ["one", "two"]


# ---------------------------------------------------------------------------
# TestLoadSettings
# ---------------------------------------------------------------------------


class TestLoadSettings:
    """Tests for _load_settings()."""

    def test_loads_from_file(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "settings.yaml",
            "default_assignee: alice\nweb_port: 9000\n",
        )
        settings = _load_settings(tmp_path)
        assert settings.default_assignee == "alice"
        assert settings.web_port == 9000

    def test_defaults_when_missing(self, tmp_path: Path) -> None:
        settings = _load_settings(tmp_path)
        assert settings == Settings()

    def test_defaults_when_empty(self, tmp_path: Path) -> None:
        _write(tmp_path / "settings.yaml", "")
        settings = _load_settings(tmp_path)
        assert settings == Settings()

    def test_partial_override(self, tmp_path: Path) -> None:
        _write(tmp_path / "settings.yaml", "claim_timeout_minutes: 60\n")
        settings = _load_settings(tmp_path)
        assert settings.claim_timeout_minutes == 60
        assert settings.web_port == 8742  # default preserved

    def test_invalid_settings_raises(self, tmp_path: Path) -> None:
        _write(tmp_path / "settings.yaml", "web_port: not-a-number\n")
        with pytest.raises(ConfigError, match="invalid settings.yaml"):
            _load_settings(tmp_path)


# ---------------------------------------------------------------------------
# TestLoadPrefixes
# ---------------------------------------------------------------------------


class TestLoadPrefixes:
    """Tests for _load_prefixes()."""

    def test_loads_prefixes(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "prefixes.yaml",
            'DIA:\n  description: "Core"\n  template: story\n'
            'EX:\n  description: "Exploration"\n  template: spike\n',
        )
        prefixes = _load_prefixes(tmp_path)
        assert "DIA" in prefixes
        assert "EX" in prefixes
        assert isinstance(prefixes["DIA"], PrefixDef)
        assert prefixes["DIA"].description == "Core"
        assert prefixes["EX"].template == "spike"

    def test_missing_returns_empty(self, tmp_path: Path) -> None:
        assert _load_prefixes(tmp_path) == {}

    def test_empty_returns_empty(self, tmp_path: Path) -> None:
        _write(tmp_path / "prefixes.yaml", "")
        assert _load_prefixes(tmp_path) == {}

    def test_default_template(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "prefixes.yaml",
            'BUG:\n  description: "Bugs"\n',
        )
        prefixes = _load_prefixes(tmp_path)
        assert prefixes["BUG"].template == "story"  # PrefixDef default

    def test_invalid_prefix_raises(self, tmp_path: Path) -> None:
        _write(tmp_path / "prefixes.yaml", "DIA: not-a-dict\n")
        with pytest.raises(ConfigError, match="invalid prefixes.yaml"):
            _load_prefixes(tmp_path)


# ---------------------------------------------------------------------------
# TestLoadSchema
# ---------------------------------------------------------------------------


class TestLoadSchema:
    """Tests for _load_schema()."""

    def test_loads_schema(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "schema.yaml",
            "required_fields:\n  - id\n  - title\n",
        )
        schema = _load_schema(tmp_path)
        assert "id" in schema.required_fields
        assert "title" in schema.required_fields

    def test_defaults_when_missing(self, tmp_path: Path) -> None:
        schema = _load_schema(tmp_path)
        assert schema == SchemaConfig()

    def test_required_by_status(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "schema.yaml",
            "required_by_status:\n  done:\n    - assignee\n",
        )
        schema = _load_schema(tmp_path)
        assert schema.required_by_status["done"] == ["assignee"]


# ---------------------------------------------------------------------------
# TestLoadPriority
# ---------------------------------------------------------------------------


class TestLoadPriority:
    """Tests for _load_priority()."""

    def test_loads_priority(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "priority.yaml",
            "weights:\n  business_value: 2.0\n  age_bonus_per_day: 1.0\n",
        )
        config = _load_priority(tmp_path)
        assert config.weights.business_value == 2.0
        assert config.weights.age_bonus_per_day == 1.0

    def test_defaults_when_missing(self, tmp_path: Path) -> None:
        config = _load_priority(tmp_path)
        assert config == PriorityConfig()

    def test_nested_due_date_urgency(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "priority.yaml",
            "weights:\n"
            "  due_date_urgency:\n"
            "    critical_days: 5\n"
            "    warning_bonus: 100.0\n",
        )
        config = _load_priority(tmp_path)
        assert config.weights.due_date_urgency.critical_days == 5
        assert config.weights.due_date_urgency.warning_bonus == 100.0


# ---------------------------------------------------------------------------
# TestLoadSprints
# ---------------------------------------------------------------------------


class TestLoadSprints:
    """Tests for _load_sprints()."""

    def test_loads_sprints(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "sprints.yaml",
            "sprints:\n"
            '  - name: "Sprint 1"\n'
            "    start: 2026-03-24\n"
            "    end: 2026-04-07\n"
            '    goal: "Core library"\n',
        )
        sprints = _load_sprints(tmp_path)
        assert len(sprints) == 1
        assert isinstance(sprints[0], Sprint)
        assert sprints[0].name == "Sprint 1"
        assert sprints[0].start == date(2026, 3, 24)
        assert sprints[0].end == date(2026, 4, 7)
        assert sprints[0].goal == "Core library"

    def test_missing_returns_empty(self, tmp_path: Path) -> None:
        assert _load_sprints(tmp_path) == []

    def test_comments_only_returns_empty(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "sprints.yaml",
            "# sprints:\n#   - name: Sprint 1\n",
        )
        assert _load_sprints(tmp_path) == []

    def test_no_sprints_key_returns_empty(self, tmp_path: Path) -> None:
        _write(tmp_path / "sprints.yaml", "other_key: value\n")
        assert _load_sprints(tmp_path) == []

    def test_multiple_sprints(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "sprints.yaml",
            "sprints:\n"
            '  - name: "S1"\n'
            "    start: 2026-03-24\n"
            "    end: 2026-04-07\n"
            '  - name: "S2"\n'
            "    start: 2026-04-07\n"
            "    end: 2026-04-21\n",
        )
        sprints = _load_sprints(tmp_path)
        assert len(sprints) == 2
        assert sprints[1].name == "S2"

    def test_invalid_sprint_raises(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "sprints.yaml",
            "sprints:\n"
            '  - name: "Bad Sprint"\n'
            "    start: not-a-date\n"
            "    end: 2026-04-07\n",
        )
        with pytest.raises(ConfigError, match="invalid sprints.yaml"):
            _load_sprints(tmp_path)


# ---------------------------------------------------------------------------
# TestLoadHooks
# ---------------------------------------------------------------------------


class TestLoadHooks:
    """Tests for _load_hooks()."""

    def test_loads_hooks(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "hooks.yaml",
            "hooks:\n"
            "  on_status_change:\n"
            "    - when:\n"
            "        status: done\n"
            "      action: move_to_archive\n",
        )
        hooks = _load_hooks(tmp_path)
        assert len(hooks.on_status_change) == 1
        assert hooks.on_status_change[0].action == "move_to_archive"
        assert hooks.on_status_change[0].when is not None
        assert hooks.on_status_change[0].when.status == "done"

    def test_missing_returns_default(self, tmp_path: Path) -> None:
        hooks = _load_hooks(tmp_path)
        assert hooks == HooksConfig()

    def test_comments_only_returns_default(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "hooks.yaml",
            "# hooks:\n#   on_status_change:\n",
        )
        hooks = _load_hooks(tmp_path)
        assert hooks == HooksConfig()

    def test_no_hooks_key_returns_default(self, tmp_path: Path) -> None:
        _write(tmp_path / "hooks.yaml", "something_else: true\n")
        hooks = _load_hooks(tmp_path)
        assert hooks == HooksConfig()

    def test_on_create_hooks(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "hooks.yaml",
            "hooks:\n  on_create:\n    - action: validate_frontmatter\n",
        )
        hooks = _load_hooks(tmp_path)
        assert len(hooks.on_create) == 1
        assert hooks.on_create[0].action == "validate_frontmatter"


# ---------------------------------------------------------------------------
# TestLoadTemplates
# ---------------------------------------------------------------------------


class TestLoadTemplates:
    """Tests for _load_templates()."""

    def test_loads_templates(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "story.md").write_text("## Description\n", encoding="utf-8")
        (tpl_dir / "epic.md").write_text("## Vision\n", encoding="utf-8")

        templates = _load_templates(tmp_path)
        assert "story" in templates
        assert "epic" in templates
        assert templates["story"] == "## Description\n"
        assert templates["epic"] == "## Vision\n"

    def test_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        assert _load_templates(tmp_path) == {}

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "templates").mkdir()
        assert _load_templates(tmp_path) == {}

    def test_ignores_non_md_files(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "story.md").write_text("## Story\n", encoding="utf-8")
        (tpl_dir / "notes.txt").write_text("ignore me\n", encoding="utf-8")

        templates = _load_templates(tmp_path)
        assert "story" in templates
        assert "notes" not in templates

    def test_stem_as_key(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "my-custom-template.md").write_text("custom\n", encoding="utf-8")

        templates = _load_templates(tmp_path)
        assert "my-custom-template" in templates


# ---------------------------------------------------------------------------
# TestDiatagmaConfig
# ---------------------------------------------------------------------------


class TestDiatagmaConfig:
    """Integration tests for DiatagmaConfig."""

    def test_loads_all_from_populated_dir(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        _write(config_dir / "settings.yaml", "web_port: 9999\n")
        _write(
            config_dir / "prefixes.yaml",
            'DIA:\n  description: "Core"\n',
        )
        _write(
            config_dir / "schema.yaml",
            "required_fields:\n  - id\n",
        )
        _write(
            config_dir / "priority.yaml",
            "weights:\n  business_value: 3.0\n",
        )
        _write(
            config_dir / "sprints.yaml",
            'sprints:\n  - name: "S1"\n    start: 2026-03-24\n    end: 2026-04-07\n',
        )
        _write(
            config_dir / "hooks.yaml",
            "hooks:\n  on_create:\n    - action: validate\n",
        )
        tpl_dir = config_dir / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "story.md").write_text("## Description\n", encoding="utf-8")

        cfg = DiatagmaConfig(tmp_path)

        assert cfg.tasks_dir == tmp_path
        assert cfg.settings.web_port == 9999
        assert "DIA" in cfg.prefixes
        assert "id" in cfg.schema.required_fields
        assert cfg.priority.weights.business_value == 3.0
        assert len(cfg.sprints) == 1
        assert len(cfg.hooks.on_create) == 1
        assert "story" in cfg.templates

    def test_defaults_for_missing_config_dir(self, tmp_path: Path) -> None:
        """No config/ dir at all — everything defaults."""
        cfg = DiatagmaConfig(tmp_path)

        assert cfg.settings == Settings()
        assert cfg.prefixes == {}
        assert cfg.schema == SchemaConfig()
        assert cfg.priority == PriorityConfig()
        assert cfg.sprints == []
        assert cfg.hooks == HooksConfig()
        assert cfg.templates == {}

    def test_partial_config(self, tmp_path: Path) -> None:
        """Only some config files present — missing ones default."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        _write(config_dir / "settings.yaml", "web_port: 7777\n")

        cfg = DiatagmaConfig(tmp_path)
        assert cfg.settings.web_port == 7777
        assert cfg.prefixes == {}
        assert cfg.sprints == []

    def test_malformed_yaml_propagates(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        _write(config_dir / "settings.yaml", "key: [unclosed\n")

        with pytest.raises(ConfigError):
            DiatagmaConfig(tmp_path)

    def test_loads_real_config(self) -> None:
        """Smoke test: load the actual .tasks/ config from this repo."""
        tasks_dir = Path(__file__).resolve().parent.parent / ".tasks"
        if not (tasks_dir / "config").exists():
            pytest.skip("repo .tasks/config not available")

        cfg = DiatagmaConfig(tasks_dir)
        assert cfg.settings.web_port == 8742
        assert "DIA" in cfg.prefixes
        assert cfg.prefixes["DIA"].template == "story"
        assert len(cfg.schema.required_fields) > 0
        assert "story" in cfg.templates
        assert "epic" in cfg.templates
        assert "spike" in cfg.templates
