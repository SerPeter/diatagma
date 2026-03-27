"""CLI entry point — ``diatagma`` command.

Subcommands:
    serve    — start the web API server (backend for React dashboard)
    mcp      — start the MCP server (stdio or SSE)
    init     — scaffold a .tasks/ directory in the current project
    validate — check all spec files against the configured schema
"""

import typer

app = typer.Typer(
    name="diatagma",
    help="Spec-driven story coordination for humans and AI agents.",
    no_args_is_help=True,
)
