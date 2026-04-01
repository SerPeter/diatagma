"""Archive commands — archive done specs or cycle specs."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json, print_success, print_warning
from diatagma.cli.state import GlobalState


@app.command()
def archive(
    done: Annotated[
        bool,
        typer.Option("--done", help="Archive all specs with terminal status."),
    ] = False,
) -> None:
    """Archive completed specs."""
    if not done:
        typer.echo("Use --done to archive all terminal specs.")
        raise typer.Exit(code=2)

    ctx = GlobalState.get_context()
    all_specs = ctx.store.list(include_archive=False)
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
