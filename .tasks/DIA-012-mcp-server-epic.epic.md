---
id: DIA-012
title: "Epic: MCP server — AI agent task interface"
status: pending
type: epic
tags: [mcp, epic]
business_value: 700
story_points: 13
dependencies: [DIA-011]
assignee: ""
created: 2026-03-27
---

## Description

Build the FastMCP 3.x server that exposes task operations as typed MCP tools for AI agents.

## Context

This is the primary interface for AI agents to discover, claim, and work on tasks. Tool schemas must be self-documenting to minimize hallucination. The server is a thin wrapper — all logic lives in core.

## Requirements

- [ ] FastMCP server with stdio and SSE transport (DIA-009)
- [ ] Full tool suite: create, get, update, list, get_next, search, claim, release, graph, validate
- [ ] Agent ID tracking for changelog attribution
- [ ] Claim/release with configurable timeout

## Acceptance Criteria

- [ ] All MCP tools callable and return valid typed responses
- [ ] `get_next_task` respects dependency DAG and priority scoring
- [ ] Agent can complete a full workflow: discover → claim → work → update → complete
- [ ] Tool schemas render correctly in MCP client introspection

## Implementation Details
