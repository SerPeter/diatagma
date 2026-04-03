"""FastMCP server setup — creates the server instance and registers all handlers.

Entry point for ``diatagma mcp`` CLI command.

Key function:
    create_mcp_server(specs_dir) → FastMCP
"""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from diatagma.core.cache import SpecCache
from diatagma.mcp.prompts import register_prompts
from diatagma.mcp.resources import register_resources
from diatagma.mcp.tools import register_tools

_INSTRUCTIONS = """\
You are interacting with a diatagma spec store — a collection of markdown \
spec files with YAML frontmatter that track work items (stories, epics, \
spikes, bugs).

Use `get_ready_specs` to find actionable work ranked by priority. \
Use `claim_spec` before starting work on a spec. \
Use `get_spec` to read full spec content. \
Use `validate_specs` to check for inconsistencies.

Spec IDs follow the pattern PREFIX-NNN (e.g. DIA-001).
"""


def create_mcp_server(specs_dir: Path) -> FastMCP:
    """Create a configured FastMCP server for the given specs directory.

    Reads go through the SQLite cache (mtime-validated) for performance.
    Mutations go through SpecStore, then update the cache.
    """
    mcp = FastMCP(
        name="diatagma",
        instructions=_INSTRUCTIONS,
        version="0.1.0",
    )

    cache = SpecCache(specs_dir / ".cache")

    register_tools(mcp, specs_dir, cache)
    register_resources(mcp, specs_dir)
    register_prompts(mcp, specs_dir)

    return mcp


__all__ = ["create_mcp_server"]
