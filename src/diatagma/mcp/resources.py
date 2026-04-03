"""MCP resource definitions — read-only spec content and configuration.

Resources provide data without consuming tool-call tokens. They are
accessed via URI (e.g. ``spec://DIA-001``, ``config://settings``).

Key function:
    register_resources(mcp, specs_dir) → None
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

from diatagma.core.context import create_context
from diatagma.core.parser import render_spec


# ---------------------------------------------------------------------------
# Resource registration
# ---------------------------------------------------------------------------


def register_resources(mcp: FastMCP, specs_dir: Path) -> None:
    """Register all MCP resources on the server instance."""

    @mcp.resource(
        "spec://{spec_id}",
        description="Full spec content (frontmatter + body) as markdown.",
        mime_type="text/markdown",
    )
    def spec_resource(spec_id: str) -> str:
        """Read a spec as rendered markdown."""
        ctx = create_context(specs_dir)
        spec = ctx.store.get(spec_id)
        return render_spec(spec)

    @mcp.resource(
        "config://settings",
        description="Current diatagma settings (statuses, types, point scale, etc.).",
        mime_type="application/json",
    )
    def settings_resource() -> str:
        """Read the active settings configuration."""
        ctx = create_context(specs_dir)
        return json.dumps(ctx.config.settings.model_dump(mode="json"))

    @mcp.resource(
        "config://statuses",
        description="Available spec status values.",
        mime_type="application/json",
    )
    def statuses_resource() -> str:
        """Read the list of valid statuses."""
        ctx = create_context(specs_dir)
        return json.dumps({"statuses": ctx.config.settings.statuses})

    @mcp.resource(
        "config://templates",
        description="Available spec templates and their content.",
        mime_type="application/json",
    )
    def templates_resource() -> str:
        """Read available templates keyed by name."""
        ctx = create_context(specs_dir)
        return json.dumps({"templates": list(ctx.config.templates.keys())})
