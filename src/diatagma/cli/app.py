"""Typer application with global options and command registration."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from loguru import logger

from diatagma.cli.state import GlobalState

app = typer.Typer(
    name="diatagma",
    help="Spec-driven story coordination for humans and AI agents.",
    no_args_is_help=True,
)


@app.callback()
def main(
    specs_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--specs-dir",
            help="Path to .specs/ directory.",
            envvar="DIATAGMA_SPECS_DIR",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-essential output."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable colored output."),
    ] = False,
) -> None:
    """Spec-driven story coordination for humans and AI agents."""
    # Configure loguru: CLI only shows warnings and above
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    GlobalState.specs_dir = specs_dir or Path.cwd() / ".specs"
    GlobalState.json = json_output
    GlobalState.quiet = quiet
    GlobalState.no_color = no_color


# Register commands (imported after app is defined to avoid circular imports)
from diatagma.cli.commands import archive  # noqa: E402, F401
from diatagma.cli.commands import graph  # noqa: E402, F401
from diatagma.cli.commands import init  # noqa: E402, F401
from diatagma.cli.commands import server  # noqa: E402, F401
from diatagma.cli.commands import spec  # noqa: E402, F401
from diatagma.cli.commands import validate  # noqa: E402, F401
