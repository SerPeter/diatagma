"""Validate command — check all specs for consistency issues."""

from __future__ import annotations

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json, print_success
from diatagma.cli.state import GlobalState


@app.command()
def validate() -> None:
    """Check all specs for schema violations, dependency cycles, and inconsistencies."""
    ctx = GlobalState.get_context()
    all_specs = ctx.refresh_graph()

    # Lifecycle consistency checks
    issues = ctx.lifecycle.validate_consistency(
        all_specs=all_specs,
        cycles=ctx.config.cycles,
    )

    # Dependency cycle detection
    dep_cycles = ctx.graph.detect_cycles()
    for cycle in dep_cycles:
        cycle_str = " → ".join(cycle)
        issues.append(
            type(
                "FakeIssue",
                (),
                {
                    "type": "circular_dependency",
                    "spec_id": cycle[0],
                    "message": f"Circular dependency: {cycle_str}",
                    "auto_corrected": False,
                },
            )()  # type: ignore[call-arg]
        )

    if GlobalState.json:
        print_json(
            [
                {
                    "type": i.type,
                    "spec_id": i.spec_id,
                    "message": i.message,
                    "auto_corrected": i.auto_corrected,
                }
                for i in issues
            ]
        )
        if issues:
            raise typer.Exit(code=1)
        return

    if not issues:
        print_success("All specs are consistent.")
        return

    for issue in issues:
        prefix = "[fixed]" if issue.auto_corrected else "[warn] "
        typer.echo(f"  {prefix} {issue.message}")

    auto_fixed = sum(1 for i in issues if i.auto_corrected)
    warnings = len(issues) - auto_fixed
    typer.echo("")
    if auto_fixed:
        typer.echo(f"  {auto_fixed} issue(s) auto-corrected.")
    if warnings:
        typer.echo(f"  {warnings} warning(s) require attention.")
        raise typer.Exit(code=1)
