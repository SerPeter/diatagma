"""Validate command — check all specs for consistency issues."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json, print_success, print_warning
from diatagma.cli.state import GlobalState
from diatagma.core.duplicates import auto_fix_duplicates, detect_duplicate_ids
from diatagma.core.models import ConsistencyIssue


@app.command()
def validate(
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Auto-fix duplicate IDs."),
    ] = False,
) -> None:
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

    # Duplicate ID detection
    duplicates = detect_duplicate_ids(ctx.store)
    if duplicates and fix:
        fixed_issues, warnings = auto_fix_duplicates(ctx.store, duplicates)
        issues.extend(fixed_issues)
        for w in warnings:
            print_warning(w)
    elif duplicates:
        for group in duplicates:
            files_str = ", ".join(p.name for p in group.files)
            issues.append(
                ConsistencyIssue(
                    type="duplicate_id",
                    spec_id=group.spec_id,
                    message=f"Duplicate ID {group.spec_id}: {files_str}",
                    auto_corrected=False,
                )
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
    warnings_count = len(issues) - auto_fixed
    typer.echo("")
    if auto_fixed:
        typer.echo(f"  {auto_fixed} issue(s) auto-corrected.")
    if warnings_count:
        typer.echo(f"  {warnings_count} warning(s) require attention.")
        raise typer.Exit(code=1)
