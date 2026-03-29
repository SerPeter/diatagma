---
id: DIA-009
title: "Build FastMCP server with tools, resources, and prompts"
status: pending
type: feature
tags: [mcp, agents]
business_value: 500
story_points: 8
parent: DIA-012
assignee: ""
created: 2026-03-27
updated: 2026-03-29
links:
  blocked_by: [DIA-003, DIA-005, DIA-006, DIA-008, DIA-014, DIA-015]
---

## Description

Implement the MCP server using FastMCP 3.x, exposing spec operations as typed tools, read-only spec content as resources, and workflow templates as prompts.

## Context

This is how AI agents interact with diatagma. The design must learn from widespread pain points in the ecosystem: in-memory state corruption from cached session data, excessive token consumption from bloated tool schemas, and missing rate-limit feedback that leaves agents unable to recover from throttling. The server must be a stateless, thin wrapper over core — every operation re-reads current state from the filesystem, never from an in-memory cache.

## Behavior

### Scenario: Agent discovers available specs

- **Given** a connected MCP client
- **When** the agent lists resources
- **Then** it receives URI-addressable spec content (e.g., `spec://DIA-001`) without consuming tool-call tokens

### Scenario: Agent finds ready work

- **Given** specs exist with dependencies, some completed and some pending
- **When** the agent calls `get_ready_specs`
- **Then** it receives only specs whose dependencies are fully satisfied, ranked by priority score

### Scenario: Agent claims and works on a spec

- **Given** a ready spec exists
- **When** the agent calls `claim_spec` with its agent ID
- **Then** the spec is marked in-progress with the agent's ID, and other agents see it as claimed

### Scenario: Agent uses workflow prompt

- **Given** the agent wants to create a new story
- **When** it invokes the `create-story` prompt
- **Then** it receives a structured message sequence guiding it through title, description, dependencies, and acceptance criteria

## Constraints

- **Token budget:** Total tool schema overhead must stay under 5,000 tokens. Community consensus is that 8-12 tools is the sweet spot; beyond 15, split into separate servers.
- **Stateless design:** No in-memory caching of spec state between tool calls. Stale caches are the most commonly reported cause of data corruption in similar tools.
- **Transport:** Support both stdio (for IDE integration) and Streamable HTTP (for remote/multi-agent). SSE transport is being deprecated in the MCP specification.
- **Error responses:** All errors must include structured information. Rate-limit errors must include `retryAfter` — tools that omit this leave agents unable to recover gracefully.

## Requirements

### Tools (target: 8-12)
- [ ] `get_spec` — retrieve a single spec by ID
- [ ] `list_specs` — filtered/sorted spec listing with cursor-based pagination
- [ ] `get_ready_specs` — deterministic "what's actionable?" query (unblocked + ranked)
- [ ] `create_spec` — create from template with validated frontmatter
- [ ] `update_spec` — modify frontmatter and/or body sections
- [ ] `claim_spec` / `release_spec` — agent work assignment with timeout
- [ ] `search_specs` — full-text search via SQLite FTS5 cache
- [ ] `validate_specs` — check all specs for schema violations and dependency cycles
- [ ] `get_dependency_graph` — export DAG as JSON for visualization or agent reasoning

### Resources (read-only, no side effects)
- [ ] `spec://{id}` — individual spec content (frontmatter + body)
- [ ] `config://settings` — current configuration
- [ ] `config://statuses` — available status values
- [ ] `config://templates` — available spec templates

### Prompts (workflow templates)
- [ ] `create-story` — guided story creation with required fields
- [ ] `run-spike` — spike workflow: research questions, findings, deliverables
- [ ] `triage-backlog` — review and prioritize pending backlog items

### Infrastructure
- [ ] Agent ID tracking for changelog attribution
- [ ] Pydantic models for all input/output schemas
- [ ] Cursor-based pagination (opaque tokens, not page numbers)

## Verification

- [ ] All tools callable via MCP protocol and return valid typed responses
- [ ] `get_ready_specs` returns only unblocked specs in priority order
- [ ] `claim_spec` prevents concurrent work on same spec
- [ ] Resources are accessible without consuming tool-call token budget
- [ ] Total tool schema tokens measured and documented (must be <5k)
- [ ] Statelessness test: modify a spec file externally, next tool call reflects the change

## References

- [ADR-001: FastMCP over official SDK](docs/adr/001-use-fastmcp-over-official-sdk.md)
- [MCP Resources specification](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)
- [MCP Prompts specification](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

## Implementation Notes
