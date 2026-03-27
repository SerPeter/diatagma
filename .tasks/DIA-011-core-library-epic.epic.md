---
id: DIA-011
title: "Epic: Core library — models, parser, store, cache, graph, priority"
status: pending
type: epic
tags: [core, epic]
business_value: 800
story_points: 21
dependencies: []
assignee: ""
created: 2026-03-27
---

## Description

Build the shared core library that all interfaces (MCP, web, CLI) depend on.

## Context

Core is the only layer that touches the filesystem. It owns models, parsing, CRUD, caching, dependency resolution, priority scoring, changelog, search, schema validation, and configuration loading. Getting this right first means MCP and web are thin wrappers.

## Requirements

- [ ] Pydantic models for all task metadata, body sections, and configuration (DIA-001)
- [ ] Round-tripping markdown+YAML frontmatter parser (DIA-002)
- [ ] TaskStore with full CRUD over the filesystem (DIA-003)
- [ ] SQLite read cache with mtime invalidation (DIA-004)
- [ ] networkx dependency DAG with blocking semantics (DIA-005)
- [ ] WSJF priority scoring and ranking (DIA-006)
- [ ] Append-only changelog (DIA-007)
- [ ] Configuration loader (DIA-008)

## Acceptance Criteria

- [ ] All child tasks (DIA-001 through DIA-008) are done
- [ ] `from diatagma.core import TaskStore` works end-to-end: create, read, update, list, filter, sort, search
- [ ] Dependency resolution correctly identifies blocked/unblocked tasks
- [ ] Priority ranking produces sensible ordering
- [ ] Full test coverage for all core modules

## Implementation Details
