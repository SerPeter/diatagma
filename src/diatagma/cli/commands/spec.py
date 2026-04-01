"""Spec CRUD commands: create, show, list, next, status, edit."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from pydantic import ValidationError

from diatagma.cli.output import (
    print_error,
    print_json,
    print_spec_detail,
    print_spec_row,
    print_success,
)
from diatagma.cli.state import GlobalState
from diatagma.core.models import SortField, SpecFilter
from diatagma.core.next import get_next
from diatagma.core.store import SpecNotFoundError

# Lazy import app to avoid circular imports
from diatagma.cli.app import app


@app.command()
def create(
    title: Annotated[str, typer.Argument(help="Title for the new spec.")],
    type: Annotated[str, typer.Option("--type", "-t", help="Spec type.")] = "feature",
    prefix: Annotated[
        Optional[str],
        typer.Option("--prefix", "-p", help="ID prefix (default: first configured)."),
    ] = None,
) -> None:
    """Create a new spec from template."""
    if not title.strip():
        print_error("Title cannot be empty.")

    ctx = GlobalState.get_context()
    resolved_prefix = prefix or next(iter(ctx.config.prefixes), None)
    if resolved_prefix is None:
        print_error("No prefixes configured. Run 'diatagma init' first.")

    try:
        all_specs = ctx.refresh_graph()
        spec = ctx.lifecycle.create_spec(
            resolved_prefix,
            title,
            agent_id="cli",
            all_specs=all_specs,
            spec_type=type,
        )
    except Exception as e:
        print_error(str(e))

    if GlobalState.json:
        print_json(spec)
    else:
        print_success(f"Created {spec.meta.id}: {spec.meta.title}")
        if spec.file_path:
            print_success(f"  -> {spec.file_path}")


@app.command()
def show(
    spec_id: Annotated[str, typer.Argument(help="Spec ID (e.g. DIA-015).")],
) -> None:
    """Display spec details."""
    ctx = GlobalState.get_context()
    try:
        spec = ctx.store.get(spec_id)
    except SpecNotFoundError:
        print_error(f"{spec_id} not found.")
    except ValidationError as e:
        print_error(f"{spec_id} has invalid frontmatter: {e}")

    if GlobalState.json:
        print_json(spec)
    else:
        print_spec_detail(spec)


@app.command(name="list")
def list_specs(
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by status.")
    ] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag.")] = None,
    type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="Filter by type.")
    ] = None,
    sort: Annotated[
        SortField, typer.Option("--sort", help="Sort field.")
    ] = SortField.ID,
    reverse: Annotated[
        bool, typer.Option("--reverse", "-r", help="Reverse sort order.")
    ] = False,
) -> None:
    """List specs with optional filters."""
    ctx = GlobalState.get_context()
    filters = SpecFilter(
        status=status,
        type=type,
        tags=[tag] if tag else None,
    )
    specs = ctx.store.list(
        filters=filters, sort_by=sort, reverse=reverse, include_archive=False,
    )

    if GlobalState.json:
        print_json(specs)
    else:
        if not specs:
            print_success("No specs found.")
            return
        for spec in specs:
            print_spec_row(spec)


@app.command(name="next")
def next_specs(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max specs to show.")] = 5,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag.")] = None,
    type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="Filter by type.")
    ] = None,
    cycle: Annotated[
        Optional[str], typer.Option("--cycle", help="Filter by cycle.")
    ] = None,
) -> None:
    """Show next actionable specs sorted by priority."""
    ctx = GlobalState.get_context()
    all_specs = ctx.refresh_graph()
    ready = get_next(
        all_specs,
        ctx.graph,
        n=limit,
        tags=[tag] if tag else None,
        type=type,
        cycle=cycle,
        config=ctx.config.priority,
    )

    if GlobalState.json:
        print_json(ready)
    else:
        if not ready:
            print_success("No actionable specs found.")
            return
        for spec in ready:
            print_spec_row(spec, show_priority=True)


@app.command()
def status(
    spec_id: Annotated[str, typer.Argument(help="Spec ID.")],
    new_status: Annotated[str, typer.Argument(help="New status.")],
    archive: Annotated[
        bool, typer.Option("--archive", help="Archive after setting terminal status.")
    ] = False,
) -> None:
    """Update a spec's status."""
    ctx = GlobalState.get_context()
    all_specs = ctx.refresh_graph()

    try:
        result = ctx.lifecycle.update_status(
            spec_id,
            new_status,
            agent_id="cli",
            graph=ctx.graph,
            all_specs=all_specs,
        )
    except Exception as e:
        print_error(str(e))

    if archive and new_status in ("done", "cancelled"):
        ctx.store.move_to_archive(spec_id, agent_id="cli")

    if GlobalState.json:
        print_json(result)
    else:
        print_success(f"{spec_id} -> {new_status}")
        if result.completion:
            c = result.completion
            if c.parent_progress:
                print_success(f"  {c.parent_progress}")
            if c.newly_unblocked:
                print_success(f"  Unblocked: {', '.join(c.newly_unblocked)}")
            if c.auto_completed_parents:
                print_success(
                    f"  Auto-completed: {', '.join(c.auto_completed_parents)}"
                )


@app.command()
def edit(
    spec_id: Annotated[str, typer.Argument(help="Spec ID.")],
    field: Annotated[
        str, typer.Option("--field", "-f", help="Frontmatter field name.")
    ],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Update a single frontmatter field."""
    ctx = GlobalState.get_context()

    # Coerce common types
    coerced: str | int | list[str] = value
    if value.isdigit():
        coerced = int(value)
    elif "," in value:
        coerced = [v.strip() for v in value.split(",")]

    try:
        spec = ctx.store.update(spec_id, agent_id="cli", **{field: coerced})
    except SpecNotFoundError:
        print_error(f"{spec_id} not found.")
    except Exception as e:
        print_error(str(e))

    if GlobalState.json:
        print_json(spec)
    else:
        print_success(f"{spec_id}.{field} -> {value}")
