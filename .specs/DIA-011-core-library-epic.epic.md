---
id: DIA-011
title: "Epic: Core library — models, parser, store, cache, graph, priority"
status: in-progress
type: epic
tags: [core, epic]
business_value: 800
story_points: 21
assignee: ""
created: 2026-03-27
updated: 2026-03-29
---

## Vision

A complete shared library that all interfaces (MCP, web, CLI) depend on. Core is the only layer that touches the filesystem.

## Context

Core owns models, parsing, CRUD, caching, dependency resolution, priority scoring, changelog, search, schema validation, configuration loading, file watching, and archive management. Getting this right first means MCP, web, and CLI are thin wrappers.

## Stories

- [x] DIA-001: Pydantic models
- [x] DIA-002: Frontmatter parser
- [x] DIA-003: SpecStore CRUD
- [x] DIA-004: SQLite cache
- [x] DIA-005: Dependency graph (networkx DAG)
- [x] DIA-006: Priority scoring (WSJF)
- [x] DIA-007: Changelog
- [x] DIA-008: Config loader
- [ ] DIA-014: Typed dependency relationships
- [ ] DIA-015: "Get ready specs" deterministic query
- [ ] DIA-018: File watcher for live updates
- [ ] DIA-019: Archive with context summaries
- [ ] DIA-021: Lifecycle automation (auto-complete, completion metadata, cycle archival)

## Verification

- [ ] All child stories are done
- [ ] `from diatagma.core import SpecStore` works end-to-end: create, read, update, list, filter, sort, search
- [ ] Dependency resolution correctly identifies blocked/unblocked specs with typed relationships
- [ ] `get_ready_specs()` returns deterministic priority-ranked results
- [ ] File watcher detects external changes and invalidates cache
- [ ] Archive summaries generated on spec archival
- [ ] Full test coverage for all core modules

## References

- [docs/architecture.md](docs/architecture.md)
