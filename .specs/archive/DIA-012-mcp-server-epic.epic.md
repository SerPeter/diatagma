---
id: DIA-012
title: "Epic: Agent & CLI interfaces — MCP server, CLI, coordination"
status: done
type: epic
tags: [mcp, cli, agents, epic]
business_value: 700
story_points: 21
links:
  blocked_by: [DIA-011]
created: 2026-03-27
updated: 2026-04-03
---

## Vision

AI agents and developers can discover, claim, and work on specs through MCP tools, CLI commands, or both — with safe multi-agent coordination.

## Context

Three interfaces share the same core: MCP server for AI agents, CLI for developers and scripting, and the coordination layer that prevents concurrent conflicts. All are thin wrappers — no business logic outside core.

## Stories

- [ ] DIA-009: FastMCP server with tools, resources, and prompts
- [ ] DIA-016: Multi-agent coordination (claim/lock semantics)
- [ ] DIA-017: AGENTS.md generation
- [ ] DIA-020: CLI interface

## Verification

- [ ] All child stories are done
- [ ] MCP: agent can complete full workflow (discover -> claim -> work -> update -> complete)
- [ ] CLI: `diatagma ready` and `diatagma validate` work end-to-end
- [ ] Multi-agent: two agents can work concurrently without data corruption
- [ ] AGENTS.md generated and parseable by AI agents
- [ ] MCP tool schemas total under 5,000 tokens
- [ ] CLI and MCP produce identical results for the same queries (same core functions)

## References

- [ADR-001: FastMCP over official SDK](docs/adr/001-use-fastmcp-over-official-sdk.md)
