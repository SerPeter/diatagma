"""Tests for roadmap generation (DIA-024)."""

from __future__ import annotations

from datetime import date

import pytest
from typer.testing import CliRunner

from diatagma.cli.app import app
from diatagma.cli.state import GlobalState
from diatagma.core.config import DiatagmaConfig
from diatagma.core.models import Cycle
from diatagma.core.roadmap import (
    generate_roadmap,
    generate_roadmap_json,
    update_roadmap_file,
    _current_cycle,
    _next_cycle,
)
from tests.conftest import seed_spec_file

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset global CLI state between tests."""
    GlobalState.reset()
    yield
    GlobalState.reset()


@pytest.fixture
def cli_specs_dir(tmp_specs_dir):
    """A tmp_specs_dir with config files for CLI tests."""
    config_dir = tmp_specs_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        "statuses: [pending, in-progress, in-review, done, cancelled]\n"
        "auto_complete_parent: true\n",
        encoding="utf-8",
    )
    (config_dir / "prefixes.yaml").write_text(
        'DIA:\n  description: "Diatagma"\n  template: story\n',
        encoding="utf-8",
    )
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    (templates_dir / "story.md").write_text(
        "## Description\n\n## Behavior\n", encoding="utf-8"
    )
    return tmp_specs_dir


def _make_config(specs_dir, cycles=None):
    """Create a DiatagmaConfig, optionally injecting cycles."""
    config = DiatagmaConfig(specs_dir)
    if cycles is not None:
        config._cycles = cycles
    return config


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


class TestCycleDetection:
    def test_current_cycle_exact_match(self):
        cycles = [
            Cycle(name="v0.1", start=date(2026, 3, 1), end=date(2026, 3, 31)),
            Cycle(name="v0.2", start=date(2026, 4, 1), end=date(2026, 4, 30)),
        ]
        result = _current_cycle(cycles, today=date(2026, 4, 15))
        assert result is not None
        assert result.name == "v0.2"

    def test_current_cycle_between_cycles(self):
        cycles = [
            Cycle(name="v0.1", start=date(2026, 3, 1), end=date(2026, 3, 15)),
            Cycle(name="v0.2", start=date(2026, 4, 1), end=date(2026, 4, 30)),
        ]
        # Between cycles — falls back to most recent past
        result = _current_cycle(cycles, today=date(2026, 3, 20))
        assert result is not None
        assert result.name == "v0.1"

    def test_current_cycle_none_when_empty(self):
        assert _current_cycle([], today=date(2026, 4, 1)) is None

    def test_next_cycle(self):
        cycles = [
            Cycle(name="v0.1", start=date(2026, 3, 1), end=date(2026, 3, 31)),
            Cycle(name="v0.2", start=date(2026, 4, 1), end=date(2026, 4, 30)),
        ]
        cur = _current_cycle(cycles, today=date(2026, 3, 15))
        nxt = _next_cycle(cycles, cur)
        assert nxt is not None
        assert nxt.name == "v0.2"

    def test_no_next_cycle(self):
        cycles = [
            Cycle(name="v0.1", start=date(2026, 3, 1), end=date(2026, 3, 31)),
        ]
        cur = _current_cycle(cycles, today=date(2026, 3, 15))
        nxt = _next_cycle(cycles, cur)
        assert nxt is None


# ---------------------------------------------------------------------------
# Roadmap generation (no cycles)
# ---------------------------------------------------------------------------


class TestGenerateRoadmap:
    def test_meta_table(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha", status="done")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Beta")
        config = _make_config(tmp_specs_dir)

        content = generate_roadmap(spec_store, config)

        assert "| Total specs | 2 |" in content
        assert "| Active (current cycle) | 2 |" in content
        assert "| Archived | 0 |" in content

    def test_epics_table(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-011", "Core Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir, "DIA-001", "Alpha", status="done", parent="DIA-011"
        )
        seed_spec_file(tmp_specs_dir, "DIA-002", "Beta", parent="DIA-011")
        config = _make_config(tmp_specs_dir)

        content = generate_roadmap(spec_store, config)

        assert "## Epics" in content
        assert "DIA-011: Core Epic" in content
        assert "| 1 | 0 | 1 |" in content

    def test_current_cycle_no_cycles(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha", status="done")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Beta")
        config = _make_config(tmp_specs_dir)

        content = generate_roadmap(spec_store, config)

        assert "## Current Cycle" in content
        assert "- [x] DIA-001: Alpha" in content
        assert "- [ ] DIA-002: Beta" in content

    def test_no_next_cycle_section_without_cycles(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        config = _make_config(tmp_specs_dir)

        content = generate_roadmap(spec_store, config)

        assert "Next Cycle" not in content

    def test_archived_specs_not_in_cycle(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Active")
        seed_spec_file(tmp_specs_dir / "archive", "DIA-002", "Archived", status="done")
        config = _make_config(tmp_specs_dir)

        content = generate_roadmap(spec_store, config)

        assert "| Archived | 1 |" in content
        # Archived spec should NOT be in cycle list
        assert (
            "DIA-002"
            not in content.split("cycle:current:start")[1].split("cycle:current:end")[0]
        )

    def test_deterministic_output(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Beta")
        config = _make_config(tmp_specs_dir)

        first = generate_roadmap(spec_store, config)
        second = generate_roadmap(spec_store, config)
        assert first == second

    def test_epic_suffix_on_epic_specs(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-011", "Core Epic", spec_type="epic")
        config = _make_config(tmp_specs_dir)

        content = generate_roadmap(spec_store, config)
        assert "DIA-011: Core Epic (epic)" in content


# ---------------------------------------------------------------------------
# Roadmap generation with cycles
# ---------------------------------------------------------------------------


class TestGenerateRoadmapWithCycles:
    def test_current_cycle_heading(self, spec_store, tmp_specs_dir):
        cycles = [
            Cycle(name="v0.3", start=date(2026, 4, 1), end=date(2026, 4, 30)),
        ]
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha", cycle="v0.3")
        config = _make_config(tmp_specs_dir, cycles=cycles)

        content = generate_roadmap(spec_store, config, today=date(2026, 4, 15))

        assert "## Current Cycle: v0.3" in content
        assert "- [ ] DIA-001: Alpha" in content

    def test_next_cycle_section(self, spec_store, tmp_specs_dir):
        cycles = [
            Cycle(name="v0.3", start=date(2026, 4, 1), end=date(2026, 4, 30)),
            Cycle(name="v0.4", start=date(2026, 5, 1), end=date(2026, 5, 31)),
        ]
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha", cycle="v0.3")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Beta", cycle="v0.4")
        config = _make_config(tmp_specs_dir, cycles=cycles)

        content = generate_roadmap(spec_store, config, today=date(2026, 4, 15))

        assert "## Next Cycle: v0.4" in content
        assert "DIA-002: Beta" in content.split("cycle:next:start")[1]

    def test_specs_without_cycle_not_in_cycle_sections(self, spec_store, tmp_specs_dir):
        cycles = [
            Cycle(name="v0.3", start=date(2026, 4, 1), end=date(2026, 4, 30)),
        ]
        seed_spec_file(tmp_specs_dir, "DIA-001", "Assigned", cycle="v0.3")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Unassigned")
        config = _make_config(tmp_specs_dir, cycles=cycles)

        content = generate_roadmap(spec_store, config, today=date(2026, 4, 15))

        cycle_section = content.split("cycle:current:start")[1].split(
            "cycle:current:end"
        )[0]
        assert "DIA-001" in cycle_section
        assert "DIA-002" not in cycle_section


# ---------------------------------------------------------------------------
# Prose preservation
# ---------------------------------------------------------------------------


class TestUpdateRoadmapFile:
    def test_preserves_prose_outside_fences(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        config = _make_config(tmp_specs_dir)

        existing = (
            "# Roadmap\n\n"
            "Some custom intro paragraph.\n\n"
            "<!-- diatagma:meta:start -->\n"
            "old meta content\n"
            "<!-- diatagma:meta:end -->\n\n"
            "More user prose here.\n\n"
            "<!-- diatagma:cycle:current:start -->\n"
            "old cycle content\n"
            "<!-- diatagma:cycle:current:end -->\n"
        )

        result = update_roadmap_file(existing, spec_store, config)

        # User prose preserved
        assert "Some custom intro paragraph." in result
        assert "More user prose here." in result
        # Fenced content updated
        assert "old meta content" not in result
        assert "old cycle content" not in result
        assert "Total specs" in result

    def test_no_fences_regenerates(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        config = _make_config(tmp_specs_dir)

        existing = "# My Old Roadmap\n\nNo fences here.\n"
        result = update_roadmap_file(existing, spec_store, config)

        # Full regeneration
        assert "<!-- diatagma:meta:start -->" in result
        assert "DIA-001: Alpha" in result


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestGenerateRoadmapJson:
    def test_structure(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-011", "Core Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir, "DIA-001", "Alpha", status="done", parent="DIA-011"
        )
        config = _make_config(tmp_specs_dir)

        data = generate_roadmap_json(spec_store, config)

        assert data["meta"]["total"] == 2
        assert len(data["epics"]) == 1
        assert data["epics"][0]["id"] == "DIA-011"
        assert data["epics"][0]["done"] == 1
        assert data["current_cycle"]["name"] is None
        assert len(data["current_cycle"]["specs"]) == 2

    def test_with_cycles(self, spec_store, tmp_specs_dir):
        cycles = [
            Cycle(name="v0.3", start=date(2026, 4, 1), end=date(2026, 4, 30)),
        ]
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha", cycle="v0.3")
        config = _make_config(tmp_specs_dir, cycles=cycles)

        data = generate_roadmap_json(spec_store, config, today=date(2026, 4, 15))

        assert data["current_cycle"]["name"] == "v0.3"
        assert len(data["current_cycle"]["specs"]) == 1


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestRoadmapCli:
    def test_generates_roadmap(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha", status="done")
        seed_spec_file(cli_specs_dir, "DIA-002", "Beta")

        result = runner.invoke(app, ["--specs-dir", str(cli_specs_dir), "roadmap"])
        assert result.exit_code == 0
        assert "Roadmap written" in result.output

        roadmap_path = cli_specs_dir / "ROADMAP.md"
        assert roadmap_path.exists()
        content = roadmap_path.read_text(encoding="utf-8")
        assert "- [x] DIA-001: Alpha" in content
        assert "- [ ] DIA-002: Beta" in content

    def test_updates_existing_roadmap(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")

        # Write initial roadmap with user prose
        roadmap_path = cli_specs_dir / "ROADMAP.md"
        roadmap_path.write_text(
            "# Roadmap\n\n"
            "Custom intro.\n\n"
            "<!-- diatagma:meta:start -->\nold\n<!-- diatagma:meta:end -->\n\n"
            "<!-- diatagma:cycle:current:start -->\nold\n<!-- diatagma:cycle:current:end -->\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["--specs-dir", str(cli_specs_dir), "roadmap"])
        assert result.exit_code == 0

        content = roadmap_path.read_text(encoding="utf-8")
        assert "Custom intro." in content
        assert "DIA-001: Alpha" in content

    def test_json_output(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")

        result = runner.invoke(
            app, ["--specs-dir", str(cli_specs_dir), "--json", "roadmap"]
        )
        assert result.exit_code == 0
        assert '"meta"' in result.output
        assert '"current_cycle"' in result.output
