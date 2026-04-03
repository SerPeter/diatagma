"""Server commands — serve (stub) and mcp (DIA-009)."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.state import GlobalState


@app.command()
def serve() -> None:
    """Start the web API server (not yet implemented - see DIA-010)."""
    typer.echo("Web API server not yet implemented (DIA-010).")
    raise typer.Exit(code=1)


@app.command()
def mcp(
    transport: Annotated[
        str,
        typer.Option("--transport", "-t", help="Transport: stdio or http."),
    ] = "stdio",
    host: Annotated[
        str,
        typer.Option("--host", help="HTTP host (only for http transport)."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", help="HTTP port (only for http transport)."),
    ] = 8741,
) -> None:
    """Start the MCP server for AI agent integration."""
    from diatagma.mcp.server import create_mcp_server

    specs_dir = GlobalState.specs_dir
    if not specs_dir.exists():
        typer.echo(f"Specs directory not found: {specs_dir}")
        typer.echo("Run 'diatagma init' first to create a .specs/ directory.")
        raise typer.Exit(code=1)

    server = create_mcp_server(specs_dir)

    if transport == "stdio":
        server.run(transport="stdio")
    elif transport in ("http", "streamable-http"):
        server.run(transport="http", host=host, port=port)
    else:
        typer.echo(f"Unknown transport: {transport!r}. Use 'stdio' or 'http'.")
        raise typer.Exit(code=1)
