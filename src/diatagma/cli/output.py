"""Terminal output formatting for CLI commands.

Handles both human-readable (rich) and machine-readable (JSON) output.
All commands call these helpers instead of printing directly.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import typer
from pydantic import BaseModel

from diatagma.core.models import Spec


def print_json(data: Any) -> None:
    """Print JSON to stdout."""
    if isinstance(data, BaseModel):
        _echo_safe(data.model_dump_json(indent=2))
    elif isinstance(data, list) and data and isinstance(data[0], BaseModel):
        items = [item.model_dump(mode="json") for item in data]
        _echo_safe(json.dumps(items, indent=2))
    else:
        _echo_safe(json.dumps(data, indent=2, default=str))


def print_spec_row(spec: Spec, *, show_priority: bool = False) -> None:
    """Print a single spec as a compact one-line summary."""
    parts = [
        spec.meta.id,
        _status_badge(spec.meta.status),
        spec.meta.title,
    ]
    if show_priority and spec.priority_score > 0:
        parts.append(f"(p={spec.priority_score:.1f})")
    if spec.meta.assignee:
        parts.append(f"@{spec.meta.assignee}")
    _echo_safe("  ".join(parts))


def print_spec_detail(spec: Spec) -> None:
    """Print spec frontmatter and body in a readable format."""
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

    # Links
    links = spec.meta.links
    if links.blocked_by:
        _echo_safe(f"  Blocked:  {', '.join(links.blocked_by)}")
    if links.relates_to:
        _echo_safe(f"  Related:  {', '.join(links.relates_to)}")

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


def print_error(msg: str) -> None:
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
