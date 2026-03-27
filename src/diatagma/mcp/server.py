"""FastMCP server setup and configuration.

Creates the FastMCP application instance, registers all tools from
tools.py, and configures transport (stdio for CLI integration,
SSE for networked access).

Entry point for ``diatagma mcp`` CLI command.
"""
