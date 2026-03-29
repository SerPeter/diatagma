---
id: DIA-014
title: "Extend dependency graph with typed relationships"
status: pending
type: feature
tags: [core, graph, dependencies]
business_value: 400
story_points: 5
parent: DIA-011
dependencies: [DIA-005]
assignee: ""
created: 2026-03-29
---

## Description

Extend the dependency graph to support typed relationships between specs, beyond simple "depends on" edges.

## Context

Plain dependency arrays (`dependencies: [DIA-001]`) only express "must complete before." Real project coordination requires richer semantics: a spec can block another, relate to it for context, supersede an older approach, or be discovered during work on a parent. Tools that support typed relationships enable smarter automation — for example, when a spec is marked `supersedes` another, the superseded spec can be auto-cancelled. The current graph only knows "blocked/not blocked," which limits both agent reasoning and human planning.

Critical design principle: **relationships are declared only on the affected spec, not on both sides.** If DIA-020 is blocked by DIA-014, only DIA-020's frontmatter states this — DIA-014 knows nothing about it from the markdown alone. The graph computes the inverse direction at query time (`get_dependents(DIA-014)` finds DIA-020 by scanning). This eliminates the two-file sync problem where bidirectional declarations inevitably drift out of sync, which is one of the most common sources of stale data in file-based task tools.

## Behavior

### Scenario: Spec declares it is blocked by another

- **Given** DIA-020 has `blocked_by: [DIA-014]`
- **When** DIA-014 is marked done
- **Then** DIA-020 becomes unblocked and appears in ready queries
- **Note** DIA-014's frontmatter is unchanged — it does not declare that it blocks DIA-020

### Scenario: Graph computes inverse relationships at query time

- **Given** DIA-020 declares `blocked_by: [DIA-014]` and DIA-014 declares nothing
- **When** `get_dependents("DIA-014")` is called
- **Then** DIA-020 is returned (computed by scanning all specs, not from DIA-014's frontmatter)

### Scenario: Spec declares it supersedes another

- **Given** DIA-030 has `supersedes: [DIA-015]`
- **When** DIA-030 is created
- **Then** DIA-015 is flagged as superseded (agents skip it, humans see visual indicator)
- **Note** DIA-015's frontmatter is unchanged — the supersession is only declared on DIA-030

### Scenario: Related specs provide context

- **Given** DIA-010 has `related_to: [DIA-009]`
- **When** an agent or human views DIA-010
- **Then** DIA-009 appears as related context (no blocking semantics)
- **Note** DIA-009 does not declare the relationship back — the graph computes it

### Scenario: Cycle detection with typed edges

- **Given** DIA-A declares `blocked_by: [DIA-B]` and DIA-B declares `blocked_by: [DIA-A]`
- **When** validation runs
- **Then** the cycle is detected and reported with the relationship types involved

## Constraints

- **Single-direction only:** relationships declared on the affected spec, never on both sides. Inverse lookups computed by graph at query time.
- Must be backward-compatible: existing `dependencies` and `blocked_by` arrays continue to work as implicit blocking relationship
- Relationship types stored in frontmatter, not a separate file
- Graph export must include edge types for visualization

## Requirements

- [ ] Define relationship types: `blocked_by`, `relates_to`, `supersedes`, `discovered_from`
- [ ] Frontmatter fields per type: `blocked_by: [ID]`, `relates_to: [ID]`, `supersedes: [ID]`, `discovered_from: ID`
- [ ] Backward compatibility: existing `dependencies` field treated as alias for `blocked_by`
- [ ] Update `TaskGraph` to store edge types on the networkx DiGraph
- [ ] Inverse queries computed from graph scan, not from target's frontmatter:
  - `get_dependents(spec_id)` — specs that declare `blocked_by` this spec
  - `get_related(spec_id)` — specs that declare `relates_to` this spec
  - `get_superseded()` — specs that any other spec declares `supersedes`
- [ ] Cycle detection on blocking edges only, reports relationship types in error messages
- [ ] Graph JSON export includes edge type metadata

## Verification

- [ ] Existing specs with plain `dependencies` arrays work unchanged
- [ ] New typed relationships are round-tripped correctly through parser
- [ ] Inverse lookups work without the target spec declaring anything
- [ ] `supersedes` relationship flags the target spec appropriately
- [ ] `relates_to` does not affect blocking/ready calculations
- [ ] Cycle detection only considers blocking edges (not relates_to)
- [ ] Graph visualization distinguishes edge types (different colors/styles)

## References

- [docs/architecture.md](docs/architecture.md) — dependency graph section

## Implementation Notes
