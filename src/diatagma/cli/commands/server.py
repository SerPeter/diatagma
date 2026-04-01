"""Server commands — stubs for serve and mcp (DIA-009, DIA-010)."""

from __future__ import annotations

import typer

from diatagma.cli.app import app


@app.command()
def serve() -> None:
    """Start the web API server (not yet implemented — see DIA-010)."""
    typer.echo("Web API server not yet implemented (DIA-010).")
    raise typer.Exit(code=1)


@app.command()
def mcp() -> None:
    """Start the MCP server (not yet implemented — see DIA-009)."""
    typer.echo("MCP server not yet implemented (DIA-009).")
    raise typer.Exit(code=1)
