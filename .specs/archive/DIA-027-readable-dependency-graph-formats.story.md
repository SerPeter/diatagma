---
id: DIA-027
title: Readable dependency graph formats
status: done
type: feature
tags: [cli, dx, graph]
business_value: 150
story_points: 2
created: 2026-07-30
updated: 2026-07-30
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

- [x] Unit tests for mermaid + tree renderers (including cycle case)
- [x] CLI test for `--format` option and unchanged JSON default
- [x] Full suite, ruff, ty pass

## References

- [[DIA-005]] dependency graph, [[DIA-026]] graph surfacing

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

New `core/graph_render.py` holds pure functions `to_mermaid` and `to_tree` over
a built `SpecGraph`. `to_mermaid` emits a `flowchart TD` with `id (status)`
node labels, blocking edges solid and other typed edges dotted+labelled.
`to_tree` emits a topologically-first indented tree of the blocking subgraph,
each blocker parenting the specs it blocks, with `(cycle)`-marked nodes for
dependency cycles (no crash). `diatagma graph --format` now accepts
`mermaid`/`tree` alongside the unchanged `json` default and existing `dot`.

## Implementation Notes

- Mermaid node IDs sanitize `-`→`_` (the label keeps the real ID).
- The graph models blocking/relates/supersedes/discovered edges, not
  parent/child — so mermaid renders those typed edges dotted rather than a
  parent hierarchy.
- A node with multiple blockers appears under each in the tree but its subtree
  expands once, guarded against infinite recursion on cycles.

## Implementation Notes
