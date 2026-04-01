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
        typer.echo(data.model_dump_json(indent=2))
    elif isinstance(data, list) and data and isinstance(data[0], BaseModel):
        items = [item.model_dump(mode="json") for item in data]
        typer.echo(json.dumps(items, indent=2))
    else:
        typer.echo(json.dumps(data, indent=2, default=str))


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
    typer.echo("  ".join(parts))


def print_spec_detail(spec: Spec) -> None:
    """Print spec frontmatter and body in a readable format."""
    typer.echo("-" * 60)
    typer.echo(f"  {spec.meta.id}: {spec.meta.title}")
    typer.echo("-" * 60)
    typer.echo(f"  Status:   {spec.meta.status}")
    typer.echo(f"  Type:     {spec.meta.type}")
    if spec.meta.tags:
        typer.echo(f"  Tags:     {', '.join(spec.meta.tags)}")
    if spec.meta.assignee:
        typer.echo(f"  Assignee: {spec.meta.assignee}")
    if spec.meta.parent:
        typer.echo(f"  Parent:   {spec.meta.parent}")
    if spec.meta.cycle:
        typer.echo(f"  Cycle:    {spec.meta.cycle}")
    if spec.meta.business_value is not None:
        typer.echo(f"  BV:       {spec.meta.business_value}")
    if spec.meta.story_points is not None:
        typer.echo(f"  Points:   {spec.meta.story_points}")
    if spec.meta.due_date:
        typer.echo(f"  Due:      {spec.meta.due_date}")
    typer.echo(f"  Created:  {spec.meta.created}")
    if spec.meta.updated:
        typer.echo(f"  Updated:  {spec.meta.updated}")

    # Links
    links = spec.meta.links
    if links.blocked_by:
        typer.echo(f"  Blocked:  {', '.join(links.blocked_by)}")
    if links.relates_to:
        typer.echo(f"  Related:  {', '.join(links.relates_to)}")

    if spec.file_path:
        typer.echo(f"  File:     {spec.file_path}")

    # Body
    if spec.raw_body and spec.raw_body.strip():
        typer.echo("")
        _echo_safe(spec.raw_body.rstrip())
    typer.echo("")


def print_success(msg: str) -> None:
    """Print a success message (suppressed in quiet mode)."""
    from diatagma.cli.state import GlobalState

    if not GlobalState.quiet:
        typer.echo(msg)


def print_warning(msg: str) -> None:
    """Print a warning to stderr."""
    typer.echo(f"Warning: {msg}", err=True)


def print_error(msg: str) -> None:
    """Print an error to stderr and exit."""
    typer.echo(f"Error: {msg}", err=True)
    raise typer.Exit(code=1)


def _echo_safe(text: str) -> None:
    """Print text, replacing unencodable characters on Windows."""
    encoding = sys.stdout.encoding or "utf-8"
    safe = text.encode(encoding, errors="replace").decode(encoding)
    typer.echo(safe)


def _status_badge(status: str) -> str:
    """Format a status string with brackets."""
    return f"[{status}]"
