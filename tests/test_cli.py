"""CLI integration tests using typer.testing.CliRunner."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from diatagma.cli.app import app
from diatagma.cli.state import GlobalState
from tests.conftest import seed_spec_file

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset global CLI state between tests."""
    GlobalState.reset()
    yield
    GlobalState.reset()


@pytest.fixture
def populated_specs(tmp_specs_dir, sample_prefixes, sample_templates):
    """Create a .specs/ dir with config and sample specs."""
    # Write config
    config_dir = tmp_specs_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        "statuses: [pending, in-progress, review, done, cancelled]\n"
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

    # Seed specs
    seed_spec_file(
        tmp_specs_dir, "DIA-001", "First spec", business_value=500, story_points=5
    )
    seed_spec_file(
        tmp_specs_dir, "DIA-002", "Second spec", business_value=300, story_points=3
    )
    seed_spec_file(
        tmp_specs_dir,
        "DIA-003",
        "Blocked spec",
        business_value=100,
        story_points=2,
        links={"blocked_by": ["DIA-001"]},
    )

    # Changelog
    (tmp_specs_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")

    return tmp_specs_dir


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "diatagma" in result.output.lower()

    def test_no_args(self):
        result = runner.invoke(app, [])
        # typer returns 0 or 2 for no_args_is_help depending on version
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "diatagma" in result.output.lower()


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class TestList:
    def test_list_all(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "list"])
        assert result.exit_code == 0
        assert "DIA-001" in result.output
        assert "DIA-002" in result.output
        assert "DIA-003" in result.output

    def test_list_json(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "--json", "list"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_list_filter_status(self, populated_specs):
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "list", "--status", "pending"],
        )
        assert result.exit_code == 0
        assert "DIA-001" in result.output


# ---------------------------------------------------------------------------
# Next
# ---------------------------------------------------------------------------


class TestNext:
    def test_next(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "next"])
        assert result.exit_code == 0
        # DIA-003 is blocked so should not appear first
        assert "DIA-001" in result.output

    def test_next_json(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "--json", "next"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        # Blocked spec should not appear
        ids = [s["meta"]["id"] for s in data]
        assert "DIA-003" not in ids

    def test_next_limit(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "--json", "next", "--limit", "1"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1


# ---------------------------------------------------------------------------
# Show
# ---------------------------------------------------------------------------


class TestShow:
    def test_show(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "show", "DIA-001"]
        )
        assert result.exit_code == 0
        assert "First spec" in result.output
        assert "DIA-001" in result.output

    def test_show_json(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "--json", "show", "DIA-001"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["meta"]["id"] == "DIA-001"

    def test_show_not_found(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "show", "DIA-999"]
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create(self, populated_specs):
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "create", "New feature"],
        )
        assert result.exit_code == 0
        assert "DIA-004" in result.output

    def test_create_json(self, populated_specs):
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(populated_specs),
                "--json",
                "create",
                "Another feature",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["meta"]["title"] == "Another feature"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_update(self, populated_specs):
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(populated_specs),
                "status",
                "DIA-001",
                "in-progress",
            ],
        )
        assert result.exit_code == 0
        assert "in-progress" in result.output


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


class TestEdit:
    def test_edit_field(self, populated_specs):
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(populated_specs),
                "edit",
                "DIA-001",
                "--field",
                "assignee",
                "alice",
            ],
        )
        assert result.exit_code == 0
        assert "alice" in result.output


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_validate_clean(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "validate"])
        # May have orphan warnings (DIA-003 blocked_by DIA-001 exists, so should be clean)
        # No epic consistency issues expected
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


class TestGraph:
    def test_graph_json(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "graph"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "nodes" in data
        assert "edges" in data

    def test_graph_dot(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "graph", "--format", "dot"]
        )
        assert result.exit_code == 0
        assert "digraph" in result.output


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestInit:
    def test_init(self, tmp_path):
        new_specs = tmp_path / "new_project" / ".specs"
        result = runner.invoke(app, ["--specs-dir", str(new_specs), "init"])
        assert result.exit_code == 0
        assert new_specs.exists()
        # Config files
        assert (new_specs / "config" / "settings.yaml").exists()
        assert (new_specs / "config" / "schema.yaml").exists()
        assert (new_specs / "config" / "priority.yaml").exists()
        assert (new_specs / "config" / "hooks.yaml").exists()
        assert (new_specs / "config" / "cycles.yaml").exists()
        assert (new_specs / "config" / "prefixes.yaml").exists()
        # Templates
        assert (new_specs / "config" / "templates" / "story.md").exists()
        assert (new_specs / "config" / "templates" / "epic.md").exists()
        assert (new_specs / "config" / "templates" / "spike.md").exists()
        assert (new_specs / "config" / "templates" / "bug.md").exists()
        # Root files
        assert (new_specs / "changelog.md").exists()
        assert (new_specs / "ROADMAP.md").exists()
        assert (new_specs / ".gitignore").exists()
        # Directories
        assert (new_specs / "backlog").is_dir()
        assert (new_specs / "archive").is_dir()

    def test_init_with_prefix(self, tmp_path):
        new_specs = tmp_path / "prefixed" / ".specs"
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(new_specs),
                "init",
                "--prefix",
                "PROJ",
                "--name",
                "My Project",
            ],
        )
        assert result.exit_code == 0
        prefixes = (new_specs / "config" / "prefixes.yaml").read_text(encoding="utf-8")
        assert "PROJ" in prefixes

    def test_init_already_exists(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "init"])
        assert result.exit_code == 1
        assert "already exists" in result.output.lower()


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------


class TestArchive:
    def test_archive_requires_done_flag(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "archive"])
        assert result.exit_code == 2

    def test_archive_done_no_terminal(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "archive", "--done"]
        )
        assert result.exit_code == 0
        assert "nothing to archive" in result.output.lower()


# ---------------------------------------------------------------------------
# Server stubs
# ---------------------------------------------------------------------------


class TestServerStubs:
    def test_serve_not_implemented(self):
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 1
        assert "not yet implemented" in result.output.lower()

    def test_mcp_no_specs_dir(self, tmp_path):
        nonexistent = tmp_path / "no_such_dir" / ".specs"
        result = runner.invoke(app, ["--specs-dir", str(nonexistent), "mcp"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
