"""Renumber command — manually renumber a spec and update all references."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_error, print_success, print_warning
from diatagma.cli.state import GlobalState
from diatagma.core.models import SPEC_ID_PATTERN

_SPEC_ID_RE = re.compile(SPEC_ID_PATTERN)


@app.command()
def renumber(
    old_id: Annotated[str, typer.Argument(help="Current spec ID to renumber.")],
    new_id: Annotated[str, typer.Argument(help="New spec ID to assign.")],
    file: Annotated[
        str | None,
        typer.Option(
            "--file",
            help="Specific filename when old_id is ambiguous (multiple files).",
        ),
    ] = None,
) -> None:
    """Manually renumber a spec and update all references."""
    if not _SPEC_ID_RE.match(old_id):
        print_error(f"Invalid spec ID: {old_id}")
    if not _SPEC_ID_RE.match(new_id):
        print_error(f"Invalid spec ID: {new_id}")

    ctx = GlobalState.get_context()

    if file:
        # Find the specific file in spec directories
        file_path = _find_file_by_name(ctx.store, file)
        if file_path is None:
            print_error(f"File not found: {file}")
    else:
        # Find by ID — error if ambiguous
        matches = _find_all_files_with_id(ctx.store, old_id)
        if len(matches) == 0:
            print_error(f"No spec found with ID: {old_id}")
        elif len(matches) > 1:
            names = ", ".join(p.name for p in matches)
            print_error(
                f"Multiple files with ID {old_id}: {names}. "
                f"Use --file to specify which one."
            )
        file_path = matches[0]

    from diatagma.core.duplicates import renumber_spec

    warnings = renumber_spec(old_id, new_id, file_path, ctx.store)

    for w in warnings:
        print_warning(w)

    new_filename = new_id + file_path.name[len(old_id) :]
    print_success(f"Renumbered {old_id} -> {new_id} ({new_filename})")


def _find_file_by_name(store: object, filename: str) -> Path | None:
    """Find a spec file by its filename across all directories."""
    from diatagma.core.store import SpecStore

    if not isinstance(store, SpecStore):
        return None
    for path in store.scan_files():
        if path.name == filename:
            return path
    return None


def _find_all_files_with_id(store: object, spec_id: str) -> list[Path]:
    """Find all spec files matching a given ID prefix."""
    from diatagma.core.store import SpecStore

    if not isinstance(store, SpecStore):
        return []
    prefix = f"{spec_id}-"
    return [p for p in store.scan_files() if p.name.startswith(prefix)]
