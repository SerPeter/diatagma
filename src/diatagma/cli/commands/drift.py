"""Drift command — report specs whose status disagrees with git history."""

from __future__ import annotations

from datetime import date

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json, print_success, print_warning
from diatagma.cli.state import GlobalState
from diatagma.core.drift import detect_drift, git_available


@app.command()
def drift() -> None:
    """Report specs whose recorded status disagrees with git history."""
    ctx = GlobalState.get_context()
    repo_root = ctx.config.specs_dir

    if not git_available(repo_root):
        if GlobalState.json:
            print_json([])
        else:
            print_warning("git not available — cannot detect drift.")
        return

    specs = ctx.store.list(include_archive=False)
    records = detect_drift(
        specs,
        repo_root,
        today=date.today(),
        stale_days=ctx.config.settings.drift_stale_days,
        terminal_statuses=ctx.config.settings.terminal_status_set,
    )

    if GlobalState.json:
        print_json(
            [
                {"spec_id": r.spec_id, "kind": r.kind, "detail": r.detail}
                for r in records
            ]
        )
        return

    if not records:
        print_success("No status drift detected.")
        return

    for record in records:
        typer.echo(f"  [{record.kind}] {record.spec_id}: {record.detail}")
    typer.echo("")
    typer.echo(f"  {len(records)} drift record(s) found.")
