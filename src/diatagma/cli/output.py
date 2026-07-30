"""Terminal output formatting for CLI commands.

Handles both human-readable (rich) and machine-readable (JSON) output.
All commands call these helpers instead of printing directly.
"""

from __future__ import annotations

import json
import sys
from typing import NoReturn
from typing import Any

import typer
from pydantic import BaseModel

from diatagma.core.checkbox import checkbox_progress
from diatagma.core.models import DEFAULT_TERMINAL_STATUSES, Notice, Spec


def print_json(data: Any) -> None:
    """Print JSON to stdout."""
    if isinstance(data, BaseModel):
        _echo_safe(data.model_dump_json(indent=2))
    elif isinstance(data, list) and data and isinstance(data[0], BaseModel):
        items = [item.model_dump(mode="json") for item in data]
        _echo_safe(json.dumps(items, indent=2))
    else:
        _echo_safe(json.dumps(data, indent=2, default=str))


_DEFAULT_TERMINAL = frozenset(DEFAULT_TERMINAL_STATUSES)


def print_spec_row(
    spec: Spec,
    *,
    show_priority: bool = False,
    epic_progress: tuple[int, int] | None = None,
    blocked_by: list[str] | None = None,
) -> None:
    """Print a single spec as a compact one-line summary."""
    parts = [
        spec.meta.id,
        _status_badge(spec.meta.status),
        spec.meta.title,
    ]
    if epic_progress is not None:
        done, total = epic_progress
        parts.append(f"[{done}/{total}]")
    if blocked_by:
        parts.append(f"[blocked by {', '.join(blocked_by)}]")
    if show_priority and spec.priority_score > 0:
        parts.append(f"(p={spec.priority_score:.1f})")
    if spec.meta.assignee:
        parts.append(f"@{spec.meta.assignee}")
    _echo_safe("  ".join(parts))


def print_epic_children(
    children: list[Spec], terminal_statuses: frozenset[str] = _DEFAULT_TERMINAL
) -> None:
    """Print an epic's children grouped by status with a progress summary."""
    if not children:
        return
    done = sum(1 for c in children if c.meta.status in terminal_statuses)
    _echo_safe("")
    _echo_safe(f"  Children ({done}/{len(children)} done):")
    for child in sorted(children, key=lambda c: c.meta.id):
        _echo_safe(f"    [{child.meta.status}]  {child.meta.id}: {child.meta.title}")


def print_spec_detail(
    spec: Spec,
    *,
    blocker_statuses: dict[str, str] | None = None,
    dependents: list[str] | None = None,
) -> None:
    """Print spec frontmatter and body in a readable format.

    When ``blocker_statuses`` is given, declared blockers show their live
    status; ``dependents`` (specs this one unblocks) prints an Unblocks line.
    """
    _echo_safe("-" * 60)
    _echo_safe(f"  {spec.meta.id}: {spec.meta.title}")
    _echo_safe("-" * 60)
    _echo_safe(f"  Status:   {spec.meta.status}")
    _echo_safe(f"  Type:     {spec.meta.type}")
    if spec.meta.tags:
        _echo_safe(f"  Tags:     {', '.join(spec.meta.tags)}")
    if spec.meta.assignee:
        _echo_safe(f"  Assignee: {spec.meta.assignee}")
    if spec.meta.parent:
        _echo_safe(f"  Parent:   {spec.meta.parent}")
    if spec.meta.cycle:
        _echo_safe(f"  Cycle:    {spec.meta.cycle}")
    if spec.meta.business_value is not None:
        _echo_safe(f"  BV:       {spec.meta.business_value}")
    if spec.meta.story_points is not None:
        _echo_safe(f"  Points:   {spec.meta.story_points}")
    if spec.meta.due_date:
        _echo_safe(f"  Due:      {spec.meta.due_date}")
    _echo_safe(f"  Created:  {spec.meta.created}")
    if spec.meta.updated:
        _echo_safe(f"  Updated:  {spec.meta.updated}")

    checked, total = checkbox_progress(spec)
    if total:
        _echo_safe(f"  Boxes:    {checked}/{total}")

    # Links
    links = spec.meta.links
    if links.blocked_by:
        if blocker_statuses is not None:
            rendered = ", ".join(
                f"{b} ({blocker_statuses.get(b, '?')})" for b in links.blocked_by
            )
        else:
            rendered = ", ".join(links.blocked_by)
        _echo_safe(f"  Blocked:  {rendered}")
    if links.relates_to:
        _echo_safe(f"  Related:  {', '.join(links.relates_to)}")
    if dependents:
        _echo_safe(f"  Unblocks: {', '.join(dependents)}")

    if spec.file_path:
        _echo_safe(f"  File:     {spec.file_path}")

    # Body
    if spec.raw_body and spec.raw_body.strip():
        _echo_safe("")
        _echo_safe(spec.raw_body.rstrip())
    _echo_safe("")


def print_success(msg: str) -> None:
    """Print a success message (suppressed in quiet mode)."""
    from diatagma.cli.state import GlobalState

    if not GlobalState.quiet:
        _echo_safe(msg)


def print_warning(msg: str) -> None:
    """Print a warning to stderr."""
    _echo_safe_err(f"Warning: {msg}")


def print_notices(notices: list[Notice]) -> None:
    """Print lifecycle notices (advisory, non-fatal) to stdout."""
    from diatagma.cli.state import GlobalState

    if GlobalState.quiet:
        return
    for notice in notices:
        _echo_safe(f"  ! {notice.message}")
        if notice.suggested_command:
            _echo_safe(f"      → {notice.suggested_command}")


def print_error(msg: str) -> NoReturn:
    """Print an error to stderr and exit."""
    _echo_safe_err(f"Error: {msg}")
    raise typer.Exit(code=1)


def _echo_safe(text: str) -> None:
    """Print text, replacing unencodable characters on Windows."""
    encoding = sys.stdout.encoding or "utf-8"
    safe = text.encode(encoding, errors="replace").decode(encoding)
    typer.echo(safe)


def _echo_safe_err(text: str) -> None:
    """Print to stderr, replacing unencodable characters on Windows."""
    encoding = sys.stderr.encoding or "utf-8"
    safe = text.encode(encoding, errors="replace").decode(encoding)
    typer.echo(safe, err=True)


def _status_badge(status: str) -> str:
    """Format a status string with brackets."""
    return f"[{status}]"
