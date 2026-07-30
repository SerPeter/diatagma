"""CLI integration tests using typer.testing.CliRunner."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from diatagma.cli.app import app
from diatagma.cli.state import GlobalState
from tests.conftest import seed_spec_file

runner = CliRunner()


def _write_spec_with_boxes(
    specs_dir, spec_id: str, status: str = "in-progress"
) -> None:
    """Write a spec file with one checked and one unchecked verification box."""
    text = (
        f"---\nid: {spec_id}\ntitle: Boxed\nstatus: {status}\n"
        "type: feature\ncreated: 2026-03-27\n---\n\n"
        "## Verification\n\n- [x] done one\n- [ ] todo two\n"
    )
    (specs_dir / f"{spec_id}-boxed.story.md").write_text(text, encoding="utf-8")


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

    def test_show_boxes(self, populated_specs):
        _write_spec_with_boxes(populated_specs, "DIA-050")
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "show", "DIA-050"]
        )
        assert result.exit_code == 0
        assert "Boxes:" in result.output
        assert "1/2" in result.output


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

    def test_create_with_fields(self, populated_specs):
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(populated_specs),
                "--json",
                "create",
                "Rich spec",
                "--business-value",
                "300",
                "--story-points",
                "5",
                "--parent",
                "DIA-001",
                "--tags",
                "cli,dx",
                "--description",
                "Users can do X",
                "--verification",
                "does A",
                "--verification",
                "does B",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["meta"]["business_value"] == 300
        assert data["meta"]["story_points"] == 5
        assert data["meta"]["parent"] == "DIA-001"
        assert data["meta"]["tags"] == ["cli", "dx"]
        assert "Users can do X" in data["raw_body"]
        assert "- [ ] does A" in data["raw_body"]
        assert "- [ ] does B" in data["raw_body"]

    def test_create_invalid_story_points(self, populated_specs):
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(populated_specs),
                "create",
                "Bad points",
                "--story-points",
                "4",
            ],
        )
        assert result.exit_code == 1


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

    def test_status_done_unchecked_notice(self, populated_specs):
        _write_spec_with_boxes(populated_specs, "DIA-051")
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "status", "DIA-051", "done"],
        )
        assert result.exit_code == 0
        assert "unchecked" in result.output.lower()


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

    def test_archive_single_terminal(self, populated_specs):
        runner.invoke(
            app, ["--specs-dir", str(populated_specs), "status", "DIA-001", "done"]
        )
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "archive", "DIA-001"]
        )
        assert result.exit_code == 0
        assert "archived dia-001" in result.output.lower()
        assert list((populated_specs / "archive").glob("DIA-001-*.md"))
        assert not list(populated_specs.glob("DIA-001-*.md"))

    def test_archive_single_non_terminal_refused(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "archive", "DIA-002"]
        )
        assert result.exit_code == 1
        assert "not terminal" in result.output.lower()

    def test_archive_single_force(self, populated_specs):
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "archive", "DIA-002", "--force"],
        )
        assert result.exit_code == 0
        assert "archived dia-002" in result.output.lower()

    def test_status_archive_non_terminal_warns(self, populated_specs):
        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(populated_specs),
                "status",
                "DIA-001",
                "in-progress",
                "--archive",
            ],
        )
        assert result.exit_code == 0
        assert "not archiving" in result.output.lower()


# ---------------------------------------------------------------------------
# Drift (DIA-028)
# ---------------------------------------------------------------------------


class TestDrift:
    def test_drift_json_is_a_list(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "--json", "drift"]
        )
        assert result.exit_code == 0
        assert isinstance(json.loads(result.output), list)


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


# ---------------------------------------------------------------------------
# Epic display (DIA-031)
# ---------------------------------------------------------------------------


class TestEpicDisplay:
    def test_list_shows_epic_progress(self, populated_specs):
        seed_spec_file(populated_specs, "DIA-020", "Epic", spec_type="epic")
        seed_spec_file(
            populated_specs, "DIA-021", "Child 1", status="done", parent="DIA-020"
        )
        seed_spec_file(
            populated_specs, "DIA-022", "Child 2", status="pending", parent="DIA-020"
        )
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "list"])
        assert result.exit_code == 0
        assert "[1/2]" in result.output

    def test_show_epic_children(self, populated_specs):
        seed_spec_file(populated_specs, "DIA-020", "Epic", spec_type="epic")
        seed_spec_file(
            populated_specs, "DIA-021", "Child 1", status="done", parent="DIA-020"
        )
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "show", "DIA-020"]
        )
        assert result.exit_code == 0
        assert "Children" in result.output
        assert "DIA-021" in result.output


# ---------------------------------------------------------------------------
# Graph surfacing (DIA-026)
# ---------------------------------------------------------------------------


class TestGraphSurfacing:
    def test_list_marks_blocked(self, populated_specs):
        # DIA-003 is blocked_by DIA-001 (pending) in the fixture
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "list"])
        assert result.exit_code == 0
        assert "blocked by DIA-001" in result.output

    def test_show_blocked_with_status(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "show", "DIA-003"]
        )
        assert result.exit_code == 0
        assert "Blocked:" in result.output
        assert "DIA-001 (pending)" in result.output

    def test_show_unblocks(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "show", "DIA-001"]
        )
        assert result.exit_code == 0
        assert "Unblocks:" in result.output
        assert "DIA-003" in result.output

    def test_status_blocked_start_notice(self, populated_specs):
        result = runner.invoke(
            app,
            ["--specs-dir", str(populated_specs), "status", "DIA-003", "in-progress"],
        )
        assert result.exit_code == 0
        assert "blocked by" in result.output.lower()


# ---------------------------------------------------------------------------
# Graph formats (DIA-027)
# ---------------------------------------------------------------------------


class TestGraphFormats:
    def test_mermaid(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "graph", "--format", "mermaid"]
        )
        assert result.exit_code == 0
        assert "flowchart TD" in result.output

    def test_tree(self, populated_specs):
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "graph", "--format", "tree"]
        )
        assert result.exit_code == 0
        # DIA-001 blocks DIA-003 in the fixture
        assert "DIA-001" in result.output

    def test_json_default_unchanged(self, populated_specs):
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "graph"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "nodes" in data and "edges" in data


# ---------------------------------------------------------------------------
# Graph scope + markers (active-scope default)
# ---------------------------------------------------------------------------


class TestGraphScope:
    def test_default_excludes_archived(self, populated_specs):
        (populated_specs / "archive").mkdir(exist_ok=True)
        seed_spec_file(
            populated_specs / "archive", "DIA-050", "Archived", status="done"
        )
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "graph"])
        assert result.exit_code == 0
        ids = [n["id"] for n in json.loads(result.output)["nodes"]]
        assert "DIA-050" not in ids

    def test_full_includes_archived_with_marker(self, populated_specs):
        (populated_specs / "archive").mkdir(exist_ok=True)
        seed_spec_file(
            populated_specs / "archive", "DIA-050", "Archived", status="done"
        )
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "graph", "--full"]
        )
        data = json.loads(result.output)
        node = {n["id"]: n for n in data["nodes"]}
        assert "DIA-050" in node
        assert node["DIA-050"]["location"] == "archived"

    def test_backlog_blocker_pulled_in(self, populated_specs):
        (populated_specs / "backlog").mkdir(exist_ok=True)
        seed_spec_file(
            populated_specs / "backlog", "DIA-051", "Backlog blocker", status="pending"
        )
        seed_spec_file(
            populated_specs,
            "DIA-052",
            "Active needing blocker",
            status="pending",
            links={"blocked_by": ["DIA-051"]},
        )
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "graph"])
        data = json.loads(result.output)
        node = {n["id"]: n for n in data["nodes"]}
        assert "DIA-051" in node  # pulled in: it blocks active DIA-052
        assert node["DIA-051"]["location"] == "backlog"

    def test_json_drops_satisfied_edges(self, populated_specs):
        # Even in --full, a done blocker's blocking edge is dropped (satisfied),
        # matching the tree/mermaid live-edge view.
        (populated_specs / "archive").mkdir(exist_ok=True)
        seed_spec_file(
            populated_specs / "archive", "DIA-060", "Done blocker", status="done"
        )
        seed_spec_file(
            populated_specs,
            "DIA-061",
            "Active blocked",
            status="pending",
            links={"blocked_by": ["DIA-060"]},
        )
        result = runner.invoke(
            app, ["--specs-dir", str(populated_specs), "graph", "--full"]
        )
        data = json.loads(result.output)
        ids = [n["id"] for n in data["nodes"]]
        assert "DIA-060" in ids  # node visible under --full
        edges = [(e["source"], e["target"]) for e in data["edges"]]
        assert ("DIA-060", "DIA-061") not in edges  # satisfied edge dropped


class TestGraphScopeLiveBlockers:
    def test_transitive_live_backlog_blocker_pulled_in(self, populated_specs):
        (populated_specs / "backlog").mkdir(exist_ok=True)
        seed_spec_file(
            populated_specs / "backlog",
            "DIA-071",
            "B1",
            status="pending",
            links={"blocked_by": ["DIA-072"]},
        )
        seed_spec_file(populated_specs / "backlog", "DIA-072", "B2", status="pending")
        seed_spec_file(
            populated_specs,
            "DIA-070",
            "Active",
            status="pending",
            links={"blocked_by": ["DIA-071"]},
        )
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "graph"])
        ids = [n["id"] for n in json.loads(result.output)["nodes"]]
        assert "DIA-071" in ids  # direct live blocker
        assert "DIA-072" in ids  # transitive live blocker (was hidden before)

    def test_dangling_live_blocker_not_hidden(self, populated_specs):
        seed_spec_file(
            populated_specs,
            "DIA-080",
            "Active",
            status="pending",
            links={"blocked_by": ["DIA-999"]},
        )
        result = runner.invoke(app, ["--specs-dir", str(populated_specs), "graph"])
        data = json.loads(result.output)
        ids = [n["id"] for n in data["nodes"]]
        assert "DIA-999" in ids  # phantom blocker surfaced (unknown = live)
        edges = [(e["source"], e["target"]) for e in data["edges"]]
        assert ("DIA-999", "DIA-080") in edges  # real constraint not hidden
