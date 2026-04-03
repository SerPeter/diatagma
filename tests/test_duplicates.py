"""Tests for spec ID collision detection and resolution (DIA-016)."""

from __future__ import annotations


import pytest
from typer.testing import CliRunner

from diatagma.cli.app import app
from diatagma.cli.state import GlobalState
from diatagma.core.duplicates import (
    auto_fix_duplicates,
    detect_duplicate_ids,
    renumber_spec,
)
from diatagma.core.parser import parse_spec_file
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
    return tmp_specs_dir


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------


class TestDetectDuplicateIds:
    def test_no_duplicates(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Beta")
        seed_spec_file(tmp_specs_dir, "DIA-003", "Gamma")

        result = detect_duplicate_ids(spec_store)
        assert result == []

    def test_detects_duplicates(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-001", "Beta")

        result = detect_duplicate_ids(spec_store)
        assert len(result) == 1
        assert result[0].spec_id == "DIA-001"
        assert len(result[0].files) == 2

    def test_multiple_duplicate_groups(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-001", "Beta")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Gamma")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Delta")

        result = detect_duplicate_ids(spec_store)
        assert len(result) == 2

    def test_slugs_extracted(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-001", "Beta")

        result = detect_duplicate_ids(spec_store)
        assert "alpha" in result[0].slugs
        assert "beta" in result[0].slugs


# ---------------------------------------------------------------------------
# Renumber tests
# ---------------------------------------------------------------------------


class TestRenumberSpec:
    def test_updates_file_and_frontmatter(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        old_path = tmp_specs_dir / "DIA-001-alpha.story.md"

        renumber_spec("DIA-001", "DIA-005", old_path, spec_store)

        # Old file should be gone
        assert not old_path.exists()

        # New file should exist with updated ID
        new_path = tmp_specs_dir / "DIA-005-alpha.story.md"
        assert new_path.exists()

        spec = parse_spec_file(new_path)
        assert spec.meta.id == "DIA-005"

    def test_updates_references_in_other_specs(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Beta",
            links={"blocked_by": ["DIA-001"]},
        )

        old_path = tmp_specs_dir / "DIA-001-alpha.story.md"
        renumber_spec("DIA-001", "DIA-005", old_path, spec_store)

        # DIA-002 should now reference DIA-005
        beta_path = tmp_specs_dir / "DIA-002-beta.story.md"
        beta = parse_spec_file(beta_path)
        assert "DIA-005" in beta.meta.links.blocked_by
        assert "DIA-001" not in beta.meta.links.blocked_by

    def test_updates_parent_reference(self, spec_store, tmp_specs_dir):
        seed_spec_file(tmp_specs_dir, "DIA-010", "Epic", spec_type="epic")
        seed_spec_file(tmp_specs_dir, "DIA-001", "Child", parent="DIA-010")

        old_path = tmp_specs_dir / "DIA-010-epic.epic.md"
        renumber_spec("DIA-010", "DIA-020", old_path, spec_store)

        child_path = tmp_specs_dir / "DIA-001-child.story.md"
        child = parse_spec_file(child_path)
        assert child.meta.parent == "DIA-020"

    def test_warns_on_ambiguous_references(self, spec_store, tmp_specs_dir):
        # Two files with same ID
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-001", "Beta")
        # A third spec references the duplicated ID
        seed_spec_file(
            tmp_specs_dir,
            "DIA-003",
            "Gamma",
            links={"blocked_by": ["DIA-001"]},
        )

        alpha_path = tmp_specs_dir / "DIA-001-alpha.story.md"
        warnings = renumber_spec("DIA-001", "DIA-005", alpha_path, spec_store)

        # Should warn because DIA-001-beta still exists
        assert len(warnings) == 1
        assert "DIA-003" in warnings[0]
        assert "DIA-001" in warnings[0]


# ---------------------------------------------------------------------------
# Auto-fix tests
# ---------------------------------------------------------------------------


class TestAutoFixDuplicates:
    def test_keeps_older_file(self, spec_store, tmp_specs_dir):
        # Create two specs with same ID, different mtimes
        seed_spec_file(tmp_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(tmp_specs_dir, "DIA-001", "Beta")

        # Ensure Alpha is "older" by touching Beta to a newer mtime
        alpha_path = tmp_specs_dir / "DIA-001-alpha.story.md"
        beta_path = tmp_specs_dir / "DIA-001-beta.story.md"

        # Make alpha older
        import os

        os.utime(alpha_path, (1000000, 1000000))
        os.utime(beta_path, (2000000, 2000000))

        duplicates = detect_duplicate_ids(spec_store)
        issues, warnings = auto_fix_duplicates(spec_store, duplicates)

        assert len(issues) == 1
        assert issues[0].auto_corrected is True

        # Alpha should still exist with DIA-001
        assert alpha_path.exists()
        alpha = parse_spec_file(alpha_path)
        assert alpha.meta.id == "DIA-001"

        # Beta should be renumbered (DIA-001-beta gone, DIA-002-beta exists)
        assert not beta_path.exists()
        new_beta = tmp_specs_dir / "DIA-002-beta.story.md"
        assert new_beta.exists()
        beta = parse_spec_file(new_beta)
        assert beta.meta.id == "DIA-002"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestValidateCli:
    def test_detects_duplicates(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(cli_specs_dir, "DIA-001", "Beta")

        result = runner.invoke(app, ["--specs-dir", str(cli_specs_dir), "validate"])
        assert result.exit_code == 1
        assert "Duplicate ID DIA-001" in result.output

    def test_fix_resolves_duplicates(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(cli_specs_dir, "DIA-001", "Beta")

        # Make Alpha older
        import os

        alpha_path = cli_specs_dir / "DIA-001-alpha.story.md"
        beta_path = cli_specs_dir / "DIA-001-beta.story.md"
        os.utime(alpha_path, (1000000, 1000000))
        os.utime(beta_path, (2000000, 2000000))

        result = runner.invoke(
            app, ["--specs-dir", str(cli_specs_dir), "validate", "--fix"]
        )
        # Should report the fix but not exit with error
        assert (
            "renumbered" in result.output.lower()
            or "auto-corrected" in result.output.lower()
        )

    def test_no_issues(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(cli_specs_dir, "DIA-002", "Beta")

        result = runner.invoke(app, ["--specs-dir", str(cli_specs_dir), "validate"])
        assert result.exit_code == 0


class TestRenumberCli:
    def test_renumber_command(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")

        result = runner.invoke(
            app,
            ["--specs-dir", str(cli_specs_dir), "renumber", "DIA-001", "DIA-005"],
        )
        assert result.exit_code == 0
        assert "DIA-005" in result.output

        # Verify file was renamed
        assert not (cli_specs_dir / "DIA-001-alpha.story.md").exists()
        assert (cli_specs_dir / "DIA-005-alpha.story.md").exists()

    def test_renumber_ambiguous_without_file(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(cli_specs_dir, "DIA-001", "Beta")

        result = runner.invoke(
            app,
            ["--specs-dir", str(cli_specs_dir), "renumber", "DIA-001", "DIA-005"],
        )
        assert result.exit_code == 1
        assert "Multiple files" in result.output or "multiple" in result.output.lower()

    def test_renumber_with_file_flag(self, cli_specs_dir):
        seed_spec_file(cli_specs_dir, "DIA-001", "Alpha")
        seed_spec_file(cli_specs_dir, "DIA-001", "Beta")

        result = runner.invoke(
            app,
            [
                "--specs-dir",
                str(cli_specs_dir),
                "renumber",
                "DIA-001",
                "DIA-005",
                "--file",
                "DIA-001-beta.story.md",
            ],
        )
        assert result.exit_code == 0
        assert "DIA-005" in result.output
