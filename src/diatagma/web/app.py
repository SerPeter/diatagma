"""FastAPI application factory.

Creates the FastAPI app, mounts static files, configures Jinja2
templates, and includes route modules. Entry point for
``diatagma serve`` CLI command.

The app shares the same core TaskStore instance used by the MCP server,
ensuring both interfaces see the same state.
"""
