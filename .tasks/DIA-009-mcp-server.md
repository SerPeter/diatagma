---
id: DIA-009
title: "Build FastMCP server with task management tools"
status: pending
type: feature
tags: [mcp, agents]
business_value: 500
story_points: 8
parent: DIA-012
dependencies: [DIA-003, DIA-005, DIA-006, DIA-008]
assignee: ""
created: 2026-03-27
---

## Description

Implement the MCP server using FastMCP 3.x, exposing task operations as tools for AI agents.

## Context

This is how AI agents interact with diatagma — through MCP tools that create, query, and update tasks. The tools must have clear schemas with typed inputs/outputs to minimize agent hallucination.

## Requirements

- [ ] FastMCP server with stdio and SSE transport options
- [ ] Tools: create_task, get_task, update_task, list_tasks, get_next_task
- [ ] Tools: search_tasks, claim_task, release_task
- [ ] Tools: get_dependency_graph, validate_tasks
- [ ] All tools use Pydantic models for input/output schemas
- [ ] Agent ID tracking for changelog attribution

## Acceptance Criteria

- [ ] All tools callable via MCP protocol and return valid responses
- [ ] get_next_task respects dependencies and priority scoring
- [ ] claim_task prevents concurrent work on same task
- [ ] Tool schemas are self-documenting (agents can discover capabilities)

## Implementation Details
