"""Tests for agents_md generation and init --skill / --agents-md flows."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from diatagma.cli.app import app
from diatagma.cli.state import GlobalState
from diatagma.core.agents_md import (
    render_agents_md_section,
    render_skill,
    render_user_preferences,
)
from tests.conftest import seed_spec_file

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_state():
    GlobalState.reset()
    yield
    GlobalState.reset()


@pytest.fixture
def populated_specs(tmp_specs_dir, sample_prefixes, sample_templates):
    """Create a .specs/ dir with config and sample specs."""
    config_dir = tmp_specs_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        "statuses: [pending, in-progress, review, done, cancelled]\n"
        "types: [feature, bug, epic, spike]\n"
        "auto_complete_parent: true\n",
        encoding="utf-8",
    )
    (config_dir / "prefixes.yaml").write_text(
        'TST:\n  description: "Test project"\n  template: story\n',
        encoding="utf-8",
    )
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    (templates_dir / "story.md").write_text(
        "## Description\n\n## Behavior\n", encoding="utf-8"
    )
    seed_spec_file(tmp_specs_dir, "TST-001", "Test spec", business_value=100)
    (tmp_specs_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    return tmp_specs_dir


# ---------------------------------------------------------------------------
# Core rendering
# ---------------------------------------------------------------------------


class TestRenderSkill:
    def test_deterministic(self):
        """Same input produces identical output."""
        a = render_skill()
        b = render_skill()
        assert a == b

    def test_contains_frontmatter(self):
        content = render_skill()
        assert "---" in content
        assert "name: diatagma" in content

    def test_contains_cli_commands(self):
        content = render_skill()
        assert "diatagma next" in content
        assert "diatagma show" in content
        assert "diatagma status" in content
        assert "diatagma create" in content
        assert "diatagma list" in content

    def test_contains_workflow(self):
        content = render_skill()
        assert "Find ready work" in content
        assert "diatagma next --json" in content

    def test_with_config(self, populated_specs):
        from diatagma.core.config import DiatagmaConfig

        config = DiatagmaConfig(populated_specs)
        content = render_skill(config)
        assert "TST" in content
        assert "Test project" in content
        assert "`pending`" in content

    def test_without_config(self):
        content = render_skill(None)
        assert "## Commands" in content
        # No project config section
        assert "## Project Configuration" not in content

    def test_references_user_preferences(self):
        content = render_skill()
        assert "user-preferences.md" in content


class TestRenderAgentsMdSection:
    def test_short(self):
        section = render_agents_md_section()
        lines = section.strip().splitlines()
        assert len(lines) <= 10

    def test_contains_marker(self):
        section = render_agents_md_section()
        assert "## Diatagma" in section

    def test_contains_next_command(self):
        section = render_agents_md_section()
        assert "diatagma next" in section

    def test_references_skill(self):
        section = render_agents_md_section()
        assert "/diatagma" in section


class TestRenderUserPreferences:
    def test_not_empty(self):
        content = render_user_preferences()
        assert len(content) > 0
        assert "User Preferences" in content


# ---------------------------------------------------------------------------
# CLI init --skill
# ---------------------------------------------------------------------------


class TestInitSkill:
    def test_skill_creates_files(self, populated_specs, tmp_path):
        # Create a fake .git so _find_repo_root works
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--skill"],
        )
        assert result.exit_code == 0

        skill_path = repo_root / ".claude" / "skills" / "diatagma" / "skill.md"
        prefs_path = (
            repo_root
            / ".claude"
            / "skills"
            / "diatagma"
            / "references"
            / "user-preferences.md"
        )
        assert skill_path.exists()
        assert prefs_path.exists()

        # Skill has project-specific content
        content = skill_path.read_text(encoding="utf-8")
        assert "TST" in content

    def test_skill_errors_when_exists(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        # First install
        runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--skill"],
        )

        # Second install should error
        GlobalState.reset()
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--skill"],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output.lower()

    def test_update_regenerates_skill(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        # First install
        runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--skill"],
        )

        # Write something to user-preferences
        prefs_path = (
            repo_root
            / ".claude"
            / "skills"
            / "diatagma"
            / "references"
            / "user-preferences.md"
        )
        prefs_path.write_text("# My custom prefs\n", encoding="utf-8")

        # Update should regenerate skill but keep prefs
        GlobalState.reset()
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--update"],
        )
        assert result.exit_code == 0

        # Skill regenerated
        skill_path = repo_root / ".claude" / "skills" / "diatagma" / "skill.md"
        assert skill_path.exists()

        # User preferences preserved
        assert prefs_path.read_text(encoding="utf-8") == "# My custom prefs\n"


# ---------------------------------------------------------------------------
# CLI init --agents-md
# ---------------------------------------------------------------------------


class TestInitAgentsMd:
    def test_warns_when_no_target(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--agents-md"],
        )
        assert result.exit_code == 0
        assert "no agents.md or claude.md found" in result.output.lower()

    def test_appends_to_agents_md(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        # Pre-existing AGENTS.md
        agents_path = repo_root / "AGENTS.md"
        agents_path.write_text("# My Project\n\nSome content.\n", encoding="utf-8")

        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--agents-md"],
        )
        assert result.exit_code == 0

        content = agents_path.read_text(encoding="utf-8")
        assert "# My Project" in content  # original preserved
        assert "## Diatagma" in content  # section appended

    def test_falls_back_to_claude_md(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        # Only CLAUDE.md exists, no AGENTS.md
        claude_path = repo_root / "CLAUDE.md"
        claude_path.write_text("# Project\n\nInstructions.\n", encoding="utf-8")

        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--agents-md"],
        )
        assert result.exit_code == 0

        content = claude_path.read_text(encoding="utf-8")
        assert "# Project" in content  # original preserved
        assert "## Diatagma" in content  # section appended
        assert "CLAUDE.md" in result.output

    def test_prefers_agents_md_over_claude_md(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        # Both exist
        (repo_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (repo_root / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")

        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--agents-md"],
        )
        assert result.exit_code == 0

        # Should append to AGENTS.md, not CLAUDE.md
        assert "## Diatagma" in (repo_root / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Diatagma" not in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")

    def test_idempotent(self, populated_specs):
        repo_root = populated_specs.parent
        (repo_root / ".git").mkdir(exist_ok=True)

        agents_path = repo_root / "AGENTS.md"
        agents_path.write_text("# Project\n", encoding="utf-8")

        # First install
        runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--agents-md"],
        )
        first_content = agents_path.read_text(encoding="utf-8")

        # Second install should skip
        GlobalState.reset()
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "init", "--agents-md"],
        )
        assert result.exit_code == 0
        assert "skipped" in result.output.lower()
        assert agents_path.read_text(encoding="utf-8") == first_content
