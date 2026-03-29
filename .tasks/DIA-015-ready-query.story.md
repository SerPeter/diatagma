---
id: DIA-015
title: "Implement deterministic 'get ready specs' query"
status: pending
type: feature
tags: [core, query, agents]
business_value: 500
story_points: 3
parent: DIA-011
assignee: ""
created: 2026-03-29
links:
  blocked_by: [DIA-005, DIA-006, DIA-014]
---

## Description

Build a single, deterministic query that answers "what can I work on right now?" — the most common question both agents and humans ask a task management system.

## Context

The most praised feature across agent task management tools is a deterministic "what's ready?" command. It combines dependency resolution (only unblocked specs), priority ranking (highest-value first), and status filtering (exclude done/cancelled) into one call. Without this, agents must chain multiple queries and reason about blocking themselves, which wastes context tokens and introduces errors. This should be the single highest-value tool in the MCP server.

## Behavior

### Scenario: Simple ready query

- **Given** 5 specs exist: 2 done, 1 blocked, 2 unblocked-pending
- **When** `get_ready_specs()` is called
- **Then** it returns the 2 unblocked-pending specs, sorted by priority score descending

### Scenario: Ready query with filters

- **Given** specs span multiple tags and types
- **When** `get_ready_specs(tags=["core"], type="feature")` is called
- **Then** only unblocked core features are returned, still priority-sorted

### Scenario: Ready query with limit

- **Given** 20 specs are ready
- **When** `get_ready_specs(limit=3)` is called
- **Then** only the top 3 by priority are returned

### Scenario: No ready specs

- **Given** all pending specs are blocked by incomplete dependencies
- **When** `get_ready_specs()` is called
- **Then** it returns an empty list (not an error)

### Scenario: Claimed specs excluded by default

- **Given** a spec is claimed by another agent
- **When** `get_ready_specs()` is called
- **Then** claimed specs are excluded unless `include_claimed=True`

## Constraints

- Must complete in <100ms for typical project sizes (<500 specs)
- Result must be deterministic: same state always produces same ordering
- Uses the SQLite cache for performance, falls back to filesystem if cache is stale

## Requirements

- [ ] `get_ready_specs(filters, limit, include_claimed) -> list[Spec]` in core
- [ ] Combines: unblocked check (graph) + status filter + priority sort + claim filter
- [ ] Optional filters: tags, type, assignee, sprint
- [ ] Deterministic tiebreaker when priority scores are equal (by ID, ascending)
- [ ] Performance target: <100ms for 500 specs

## Verification

- [ ] Returns only specs with all dependencies satisfied
- [ ] Respects priority ordering (higher score first)
- [ ] Filters work correctly (tags, type, sprint)
- [ ] Claimed specs excluded by default
- [ ] Deterministic: repeated calls with same state return same order
- [ ] Performance benchmark passes (<100ms at 500 specs)

## References

- [docs/architecture.md](docs/architecture.md) — query flow section

## Implementation Notes

Renamed from `get_ready_specs()` to `get_next()` in `core/next.py`. Takes a flat `specs` list + built `SpecGraph` instead of `SpecStore` directly. Accepts `n` parameter for limiting results (e.g. `get_next(specs, graph, n=5)`). Non-empty `assignee` is treated as "claimed" and excluded by default (`include_claimed=True` to override). Epics are always excluded. Circular dependency participants are excluded with a loguru warning.
