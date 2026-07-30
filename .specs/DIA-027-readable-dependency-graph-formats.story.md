---
id: DIA-027
title: Readable dependency graph formats
status: pending
type: feature
tags: [cli, dx, graph]
business_value: 150
story_points: 2
created: 2026-07-30
---

## Description

`diatagma graph --format mermaid` and `--format tree` render the dependency graph in forms humans and agents can read; JSON stays the default.

## Context

`diatagma graph` dumps raw node/edge JSON — fine for machines, useless for a human or an agent trying to reason about ordering. Mermaid renders in GitHub and the dashboard; a topologically-sorted tree reads directly in the terminal. Rendering lives in `core` as pure functions over `SpecGraph` so web/MCP can reuse it.

## Behavior

### Scenario: mermaid output

- **Given** specs with blocking and parent edges
- **When** `diatagma graph --format mermaid` runs
- **Then** output is a `flowchart TD` with one node per spec (id + status) and typed edges (blocking solid, parent/child dotted)

### Scenario: tree output

- **Given** specs with blocking edges
- **When** `diatagma graph --format tree` runs
- **Then** specs print in topological order, each blocker parenting its dependents by indentation, statuses shown

### Scenario: default unchanged

- **Given** any specs
- **When** `diatagma graph` runs without `--format`
- **Then** output is the existing JSON shape, byte-compatible with today

### Scenario: cycles don't crash tree rendering

- **Given** a dependency cycle exists
- **When** `--format tree` runs
- **Then** the command still renders, marking the cycle rather than raising

## Constraints

- No new dependencies — string building only.
- Renderers are pure functions in `core`, testable without the CLI.

## Verification

- [ ] Unit tests for mermaid + tree renderers (including cycle case)
- [ ] CLI test for `--format` option and unchanged JSON default
- [ ] Full suite, ruff, ty pass

## References

- [[DIA-005]] dependency graph, [[DIA-026]] graph surfacing

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

## Implementation Notes
