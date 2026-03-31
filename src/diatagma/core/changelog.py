"""Append-only changelog for spec mutations.

Writes structured, diff-friendly entries to .specs/changelog.md.
One line per change, grouped by date. Git-friendly, grep-friendly.

Format:
    ## 2026-03-27
    - DIA-001: status pending -> in-progress (agent: claude-abc)
    - DIA-002: created (agent: human)
    - DIA-003: business_value 100 -> 300 (agent: human)

Key class:
    Changelog(changelog_path)
        .append_entry(spec_id, action, field, old, new, agent_id)
        .read_entries(since: date | None) -> list[ChangelogEntry]
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from diatagma.core.models import ChangelogEntry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FILE_HEADER = """\
# Changelog

<!-- Append-only log of task mutations. One line per change, grouped by date.
     Format: - TASK-ID: field old \u2192 new (agent: id) -->
"""

_DATE_HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
_ENTRY_RE = re.compile(r"^- ([A-Z]+-\d+): (.+?) \(agent: (.+?)\)\s*$")
_FIELD_CHANGE_RE = re.compile(r"^(\S+) (.+?) \u2192 (.+)$")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_line(
    spec_id: str,
    action: str,
    field: str | None = None,
    old: str | None = None,
    new: str | None = None,
    agent_id: str = "unknown",
) -> str:
    """Build a single changelog line."""
    if field is not None and old is not None and new is not None:
        body = f"{field} {old} \u2192 {new}"
    else:
        body = action
    return f"- {spec_id}: {body} (agent: {agent_id})"


def _parse_line(line: str, current_date: date) -> ChangelogEntry | None:
    """Parse a single entry line into a ChangelogEntry, or None if malformed."""
    m = _ENTRY_RE.match(line)
    if m is None:
        return None

    spec_id, body, agent_id = m.group(1), m.group(2), m.group(3)

    # Try to parse as a field change: "field old -> new"
    fm = _FIELD_CHANGE_RE.match(body)
    if fm is not None:
        return ChangelogEntry(
            date=current_date,
            spec_id=spec_id,
            action="updated",
            field=fm.group(1),
            old=fm.group(2),
            new=fm.group(3),
            agent_id=agent_id,
        )

    return ChangelogEntry(
        date=current_date,
        spec_id=spec_id,
        action=body,
        agent_id=agent_id,
    )


def _get_last_date_header(path: Path) -> date | None:
    """Read the last ## YYYY-MM-DD header from the file."""
    if not path.exists():
        return None

    last_date: date | None = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _DATE_HEADER_RE.match(line)
            if m:
                last_date = date.fromisoformat(m.group(1))
    return last_date


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------


class Changelog:
    """Append-only changelog writer and reader.

    Implements __call__ to satisfy the ChangelogCallback protocol
    defined in store.py.
    """

    def __init__(self, changelog_path: Path) -> None:
        self._path = Path(changelog_path)

    def __call__(
        self,
        spec_id: str,
        action: str,
        field: str | None = None,
        old: str | None = None,
        new: str | None = None,
        agent_id: str = "unknown",
    ) -> None:
        """ChangelogCallback protocol entry point."""
        self.append_entry(
            spec_id, action, field=field, old=old, new=new, agent_id=agent_id
        )

    def append_entry(
        self,
        spec_id: str,
        action: str,
        field: str | None = None,
        old: str | None = None,
        new: str | None = None,
        agent_id: str = "unknown",
        today: date | None = None,
    ) -> None:
        """Append a single changelog entry, creating the file if needed."""
        if today is None:
            today = date.today()

        line = _format_line(spec_id, action, field, old, new, agent_id)
        needs_file_init = not self._path.exists() or self._path.stat().st_size == 0

        if needs_file_init:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                f.write(_FILE_HEADER)
                f.write(f"\n## {today.isoformat()}\n\n")
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            return

        last_date = _get_last_date_header(self._path)
        with open(self._path, "a", encoding="utf-8") as f:
            if last_date != today:
                f.write(f"\n## {today.isoformat()}\n\n")
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def read_entries(self, since: date | None = None) -> list[ChangelogEntry]:
        """Parse all entries from the changelog file.

        Args:
            since: If provided, only return entries on or after this date.

        Returns:
            List of ChangelogEntry objects in file order.
        """
        if not self._path.exists():
            return []

        entries: list[ChangelogEntry] = []
        current_date: date | None = None

        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")

                # Check for date header
                m = _DATE_HEADER_RE.match(line)
                if m:
                    current_date = date.fromisoformat(m.group(1))
                    continue

                # Skip non-entry lines
                if current_date is None or not line.startswith("- "):
                    continue

                entry = _parse_line(line, current_date)
                if entry is None:
                    continue

                if since is not None and entry.date < since:
                    continue

                entries.append(entry)

        return entries


__all__ = [
    "Changelog",
]
