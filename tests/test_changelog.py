"""Tests for core.changelog — append-only changelog tracking."""

from datetime import date
from pathlib import Path


from diatagma.core.changelog import (
    Changelog,
    _format_line,
    _get_last_date_header,
    _parse_line,
)
from diatagma.core.store import ChangelogCallback

TODAY = date(2026, 3, 28)
YESTERDAY = date(2026, 3, 27)


# ---------------------------------------------------------------------------
# TestFormatLine
# ---------------------------------------------------------------------------


class TestFormatLine:
    """Tests for _format_line()."""

    def test_created_action(self) -> None:
        line = _format_line("DIA-001", "created", agent_id="human")
        assert line == "- DIA-001: created (agent: human)"

    def test_field_change(self) -> None:
        line = _format_line(
            "DIA-001",
            "updated",
            field="status",
            old="pending",
            new="in-progress",
            agent_id="claude-abc",
        )
        assert (
            line == "- DIA-001: status pending \u2192 in-progress (agent: claude-abc)"
        )

    def test_move_action(self) -> None:
        line = _format_line("DIA-002", "moved to archive", agent_id="human")
        assert line == "- DIA-002: moved to archive (agent: human)"

    def test_default_agent_id(self) -> None:
        line = _format_line("DIA-003", "created")
        assert line == "- DIA-003: created (agent: unknown)"


# ---------------------------------------------------------------------------
# TestParseLine
# ---------------------------------------------------------------------------


class TestParseLine:
    """Tests for _parse_line()."""

    def test_parse_created(self) -> None:
        entry = _parse_line("- DIA-001: created (agent: human)", TODAY)
        assert entry is not None
        assert entry.spec_id == "DIA-001"
        assert entry.action == "created"
        assert entry.agent_id == "human"
        assert entry.date == TODAY

    def test_parse_field_change(self) -> None:
        entry = _parse_line(
            "- DIA-001: status pending \u2192 in-progress (agent: claude-abc)", TODAY
        )
        assert entry is not None
        assert entry.field == "status"
        assert entry.old == "pending"
        assert entry.new == "in-progress"
        assert entry.action == "updated"

    def test_parse_move(self) -> None:
        entry = _parse_line("- DIA-002: moved to archive (agent: human)", TODAY)
        assert entry is not None
        assert entry.action == "moved to archive"
        assert entry.field is None

    def test_malformed_line_returns_none(self) -> None:
        assert _parse_line("not a valid line", TODAY) is None
        assert _parse_line("- missing colon (agent: x)", TODAY) is None
        assert _parse_line("", TODAY) is None

    def test_parse_epic_field_change(self) -> None:
        """Matches the format used in the existing changelog."""
        entry = _parse_line(
            "- DIA-001: epic core-library \u2192 parent DIA-011 (agent: human)", TODAY
        )
        assert entry is not None
        assert entry.field == "epic"
        assert entry.old == "core-library"
        assert entry.new == "parent DIA-011"


# ---------------------------------------------------------------------------
# TestGetLastDateHeader
# ---------------------------------------------------------------------------


class TestGetLastDateHeader:
    """Tests for _get_last_date_header()."""

    def test_file_not_exists(self, tmp_path: Path) -> None:
        assert _get_last_date_header(tmp_path / "nope.md") is None

    def test_file_with_date_header(self, tmp_path: Path) -> None:
        f = tmp_path / "changelog.md"
        f.write_text("# Changelog\n\n## 2026-03-27\n\n- entry\n")
        assert _get_last_date_header(f) == date(2026, 3, 27)

    def test_multiple_headers_returns_last(self, tmp_path: Path) -> None:
        f = tmp_path / "changelog.md"
        f.write_text("## 2026-03-27\n\n## 2026-03-28\n\n")
        assert _get_last_date_header(f) == date(2026, 3, 28)

    def test_no_date_headers(self, tmp_path: Path) -> None:
        f = tmp_path / "changelog.md"
        f.write_text("# Changelog\n\nSome text\n")
        assert _get_last_date_header(f) is None


# ---------------------------------------------------------------------------
# TestAppendEntry
# ---------------------------------------------------------------------------


class TestAppendEntry:
    """Tests for Changelog.append_entry()."""

    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=TODAY)

        content = (tmp_path / "changelog.md").read_text(encoding="utf-8")
        assert "# Changelog" in content
        assert f"## {TODAY.isoformat()}" in content
        assert "- DIA-001: created (agent: human)" in content

    def test_appends_under_existing_date(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=TODAY)
        cl.append_entry("DIA-002", "created", agent_id="human", today=TODAY)

        content = (tmp_path / "changelog.md").read_text(encoding="utf-8")
        # Only one date header
        assert content.count(f"## {TODAY.isoformat()}") == 1
        assert "- DIA-001: created (agent: human)" in content
        assert "- DIA-002: created (agent: human)" in content

    def test_adds_new_date_header(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=YESTERDAY)
        cl.append_entry("DIA-002", "created", agent_id="human", today=TODAY)

        content = (tmp_path / "changelog.md").read_text(encoding="utf-8")
        assert f"## {YESTERDAY.isoformat()}" in content
        assert f"## {TODAY.isoformat()}" in content

    def test_field_change_entry(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry(
            "DIA-001",
            "updated",
            field="status",
            old="pending",
            new="in-progress",
            agent_id="claude-abc",
            today=TODAY,
        )

        content = (tmp_path / "changelog.md").read_text(encoding="utf-8")
        assert (
            "- DIA-001: status pending \u2192 in-progress (agent: claude-abc)"
            in content
        )

    def test_empty_file_treated_as_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "changelog.md"
        f.write_text("")
        cl = Changelog(f)
        cl.append_entry("DIA-001", "created", agent_id="human", today=TODAY)

        content = f.read_text(encoding="utf-8")
        assert "# Changelog" in content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "nested" / "dir" / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=TODAY)
        assert (tmp_path / "nested" / "dir" / "changelog.md").exists()


# ---------------------------------------------------------------------------
# TestReadEntries
# ---------------------------------------------------------------------------


class TestReadEntries:
    """Tests for Changelog.read_entries()."""

    def test_reads_all_entries(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=YESTERDAY)
        cl.append_entry("DIA-002", "created", agent_id="human", today=TODAY)

        entries = cl.read_entries()
        assert len(entries) == 2
        assert entries[0].spec_id == "DIA-001"
        assert entries[0].date == YESTERDAY
        assert entries[1].spec_id == "DIA-002"
        assert entries[1].date == TODAY

    def test_filters_by_since(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=YESTERDAY)
        cl.append_entry("DIA-002", "created", agent_id="human", today=TODAY)

        entries = cl.read_entries(since=TODAY)
        assert len(entries) == 1
        assert entries[0].spec_id == "DIA-002"

    def test_file_not_exists_returns_empty(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "nope.md")
        assert cl.read_entries() == []

    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "changelog.md"
        f.write_text(
            "# Changelog\n\n## 2026-03-28\n\n"
            "- DIA-001: created (agent: human)\n"
            "this is garbage\n"
            "- DIA-002: created (agent: human)\n"
        )
        cl = Changelog(f)
        entries = cl.read_entries()
        assert len(entries) == 2

    def test_since_future_returns_empty(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=TODAY)

        entries = cl.read_entries(since=date(2099, 1, 1))
        assert len(entries) == 0

    def test_entries_have_correct_dates(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=YESTERDAY)
        cl.append_entry(
            "DIA-001",
            "updated",
            field="status",
            old="pending",
            new="done",
            agent_id="human",
            today=TODAY,
        )

        entries = cl.read_entries()
        assert entries[0].date == YESTERDAY
        assert entries[1].date == TODAY


# ---------------------------------------------------------------------------
# TestChangelogCall
# ---------------------------------------------------------------------------


class TestChangelogCall:
    """Tests for Changelog.__call__ (ChangelogCallback protocol)."""

    def test_satisfies_protocol(self) -> None:
        cl = Changelog(Path("/tmp/test.md"))
        assert isinstance(cl, ChangelogCallback)

    def test_call_delegates_to_append_entry(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl("DIA-001", "created", agent_id="human")

        entries = cl.read_entries()
        assert len(entries) == 1
        assert entries[0].spec_id == "DIA-001"
        assert entries[0].action == "created"

    def test_call_with_field_change(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl(
            "DIA-001",
            "updated",
            field="status",
            old="pending",
            new="done",
            agent_id="bot",
        )

        entries = cl.read_entries()
        assert len(entries) == 1
        assert entries[0].field == "status"


# ---------------------------------------------------------------------------
# TestRoundTrip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Write entries then read them back."""

    def test_created_round_trip(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=TODAY)

        entries = cl.read_entries()
        assert len(entries) == 1
        e = entries[0]
        assert e.spec_id == "DIA-001"
        assert e.action == "created"
        assert e.agent_id == "human"
        assert e.date == TODAY

    def test_field_change_round_trip(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry(
            "DIA-005",
            "updated",
            field="business_value",
            old="100",
            new="300",
            agent_id="claude-xyz",
            today=TODAY,
        )

        entries = cl.read_entries()
        assert len(entries) == 1
        e = entries[0]
        assert e.field == "business_value"
        assert e.old == "100"
        assert e.new == "300"
        assert e.agent_id == "claude-xyz"

    def test_mixed_entries_round_trip(self, tmp_path: Path) -> None:
        cl = Changelog(tmp_path / "changelog.md")
        cl.append_entry("DIA-001", "created", agent_id="human", today=YESTERDAY)
        cl.append_entry(
            "DIA-001",
            "updated",
            field="status",
            old="pending",
            new="in-progress",
            agent_id="bot",
            today=YESTERDAY,
        )
        cl.append_entry("DIA-002", "created", agent_id="human", today=TODAY)
        cl.append_entry("DIA-001", "moved to archive", agent_id="bot", today=TODAY)

        entries = cl.read_entries()
        assert len(entries) == 4
        assert entries[0].action == "created"
        assert entries[1].field == "status"
        assert entries[2].action == "created"
        assert entries[3].action == "moved to archive"

    def test_reads_existing_changelog(self, tmp_path: Path) -> None:
        """Can read the format used in the real .specs/changelog.md."""
        f = tmp_path / "changelog.md"
        f.write_text(
            "# Changelog\n\n"
            "<!-- comment -->\n\n"
            "## 2026-03-27\n\n"
            "- DIA-001: created (agent: human)\n"
            "- DIA-002: created (agent: human)\n"
            "- DIA-001: epic core-library \u2192 parent DIA-011 (agent: human)\n",
            encoding="utf-8",
        )
        cl = Changelog(f)
        entries = cl.read_entries()
        assert len(entries) == 3
        assert entries[2].field == "epic"
        assert entries[2].old == "core-library"
        assert entries[2].new == "parent DIA-011"
