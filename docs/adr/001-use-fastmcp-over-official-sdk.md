# ADR-001: Use FastMCP 3.x over the official MCP Python SDK

## Status

Accepted

## Context

Diatagma needs an MCP server to expose spec operations to AI agents. Two main options exist for Python:

1. **Official MCP Python SDK** (`mcp~=1.26`) — maintained by Anthropic, bundled FastMCP 1.0 as `mcp.server.fastmcp`
2. **FastMCP 3.x** (`fastmcp~=3.1`) — standalone evolution, diverged significantly from the SDK-bundled version

The companion project (code-atlas-mcp) uses the official SDK. We evaluated both for a new project targeting Python 3.12+.

## Decision

Use **FastMCP 3.x** as the MCP server framework.

## Consequences

### Positive

- 70% MCP server market share, 1M daily downloads — de facto standard with extensive community support
- Superior decorator-based API with automatic Pydantic schema generation — reduces boilerplate
- Production features out of the box: tool versioning, granular authorization middleware, OpenTelemetry instrumentation
- 3x faster release cadence than the official SDK — bugs fixed faster, features land sooner
- Explicit Python 3.10–3.13 certification (includes our 3.12+ target)

### Negative

- Diverged from the official SDK — if Anthropic's SDK v2 brings breaking changes to the protocol, we may need to adapt
- Separate dependency from the official SDK (the project can't share MCP server code directly)

### Neutral

- Both interoperate at the protocol level — FastMCP 1.0's incorporation means wire compatibility
- The official SDK v2 (in pre-alpha) aims to "clarify the situation" but has no clear ETA

## References

- Research: `docs/research/260327_mcp-framework-comparison.md`
- FastMCP 3.0 release: https://www.jlowin.dev/blog/fastmcp-3
- Official SDK: https://github.com/modelcontextprotocol/python-sdk
- Divergence discussion: https://github.com/modelcontextprotocol/python-sdk/issues/1068
