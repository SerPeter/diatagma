"""Litestar application factory.

Creates the Litestar app, configures CORS (for React dev server),
and includes route controllers. Entry point for
``diatagma serve`` CLI command.

The app shares the same core SpecStore instance used by the MCP server,
ensuring both interfaces see the same state. In production, the React
build is served as static files from this same server.
"""
