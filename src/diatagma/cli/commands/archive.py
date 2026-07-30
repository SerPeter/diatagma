"""Archive commands — archive done specs or cycle specs."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_error, print_json, print_success, print_warning
from diatagma.cli.state import GlobalState
from diatagma.core.store import SpecNotFoundError


@app.command()
def archive(
    spec_id: Annotated[
        str | None,
        typer.Argument(help="Spec ID to archive (omit for bulk --done)."),
    ] = None,
    done: Annotated[
        bool,
        typer.Option("--done", help="Archive all specs with terminal status."),
    ] = False,
    parent: Annotated[
        str | None,
        typer.Option("--parent", help="Only archive children of this epic ID."),
    ] = None,
    cycle: Annotated[
        str | None,
        typer.Option("--cycle", help="Only archive specs in this cycle."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Archive a single spec even if not terminal."),
    ] = False,
) -> None:
    """Archive completed specs (single spec by ID, or bulk with --done)."""
    if spec_id:
        _archive_single(spec_id, force)
        return

    if not done:
        typer.echo("Use --done to archive all terminal specs, or pass a spec ID.")
        raise typer.Exit(code=2)

    ctx = GlobalState.get_context()
    all_specs = ctx.store.list(include_archive=False)

    if parent:
        all_specs = [
            s for s in all_specs if s.meta.parent == parent or s.meta.id == parent
        ]
    if cycle:
        all_specs = [s for s in all_specs if s.meta.cycle == cycle]

    result = ctx.lifecycle.archive_done(agent_id="cli", all_specs=all_specs)

    if GlobalState.json:
        print_json(result)
    else:
        if result.archived:
            print_success(f"Archived: {', '.join(result.archived)}")
        else:
            print_success("Nothing to archive.")
        for w in result.warnings:
            print_warning(w)


def _archive_single(spec_id: str, force: bool) -> None:
    """Archive one spec, guarding on terminal status unless forced."""
    ctx = GlobalState.get_context()
    try:
        spec = ctx.store.get(spec_id)
    except SpecNotFoundError:
        print_error(f"{spec_id} not found.")

    is_terminal = spec.meta.status in ctx.config.settings.terminal_status_set
    if not is_terminal and not force:
        print_error(
            f"{spec_id} is {spec.meta.status}, not terminal. "
            "Use --force to archive it anyway."
        )

    ctx.store.move_to_archive(spec_id, agent_id="cli")
    if not is_terminal:
        print_warning(f"Force-archived {spec_id} while status is {spec.meta.status}.")
    print_success(f"Archived {spec_id}.")


@app.command(name="archive-cycle")
def archive_cycle(
    cycle_name: Annotated[str, typer.Argument(help="Name of the cycle to archive.")],
) -> None:
    """Archive all terminal specs in a cycle."""
    ctx = GlobalState.get_context()
    all_specs = ctx.store.list(include_archive=False)
    result = ctx.lifecycle.archive_cycle(
        cycle_name, agent_id="cli", all_specs=all_specs
    )

    if GlobalState.json:
        print_json(result)
    else:
        if result.archived:
            print_success(f"Archived: {', '.join(result.archived)}")
        else:
            print_success(f"No terminal specs in cycle '{cycle_name}'.")
        for w in result.warnings:
            print_warning(w)
