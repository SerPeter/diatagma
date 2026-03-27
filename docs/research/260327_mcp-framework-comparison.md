# MCP Framework Comparison (2026-03-27)

## Summary

Evaluated Python MCP server frameworks for diatagma. FastMCP 3.x is the clear winner for new projects.

## Frameworks Evaluated

### Official MCP Python SDK (`mcp` package)

- **Version**: 1.7.1 (stable), v2 in pre-alpha
- **Maintainer**: Anthropic
- **Stars**: 22.4k, 838 commits
- **Python**: 3.10+
- **API**: Includes `mcp.server.fastmcp.FastMCP` (bundled FastMCP 1.0)
- **Note**: v2 aims to "clarify the situation" with standalone FastMCP (no ETA)

### FastMCP (standalone)

- **Version**: 3.1.1 (released 2026-03-14)
- **Maintainer**: jlowin (migrated from PrefectHQ)
- **Downloads**: ~1M daily, powers ~70% of MCP servers
- **Python**: 3.10–3.13 (explicit certification)
- **API**: Decorator-based with automatic Pydantic schema generation

### Key Differences (as of FastMCP 3.0+)

| Feature | Official SDK | FastMCP 3.x |
|---|---|---|
| Tool versioning | No | Yes |
| Authorization middleware | Basic | Granular per-tool |
| OpenTelemetry | Manual | Built-in |
| Component providers | No | Local, FileSystem, OpenAPI |
| Development velocity | Moderate | ~3x faster releases |
| Hot reload | No | Yes |

## Decision

→ ADR-001: Use FastMCP 3.x

## Sources

- https://github.com/jlowin/fastmcp
- https://github.com/modelcontextprotocol/python-sdk
- https://pypi.org/project/fastmcp/
- https://pypi.org/project/mcp/1.7.1/
- https://github.com/modelcontextprotocol/python-sdk/issues/1068
