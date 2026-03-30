---
id: DIA-023
title: "Rename 'sprint' to 'cycle' across codebase and config"
status: pending
type: feature
tags: [core, refactor]
business_value: 100
story_points: 2
parent: DIA-011
assignee: ""
created: 2026-03-30
links:
  blocked_by: []
  relates_to: [DIA-021]
---

## Description

Rename all references to "sprint" → "cycle" across the codebase, config files, docs, and tests. Cycles are work-bounded batches, not time-boxed iterations — the terminology should reflect that.

## Context

The term "sprint" carries Scrum/time-box connotations that don't fit this system. Specs are grouped into work-bounded batches — a cycle ends when its work is done, not when a calendar period expires. "Cycle" communicates iteration without implying fixed duration.

This is a pure rename — no behavioral changes. Separated from DIA-021 (lifecycle automation) to keep that spec focused on new functionality.

## Behavior

### Scenario: Config file renamed

- **Given** `.tasks/config/sprints.yaml` exists
- **When** the rename is applied
- **Then** the file is renamed to `.tasks/config/cycles.yaml` with `cycles:` as the top-level key (previously `sprints:`)

### Scenario: Frontmatter field renamed

- **Given** a spec has `sprint: "Sprint 1"` in frontmatter
- **When** the spec is parsed
- **Then** the field is `cycle: "Cycle 1"` (note: existing spec files in `.tasks/` need migration only if they use the field)

### Scenario: Code references updated

- **Given** `SpecMeta.sprint`, `Sprint` model, `SpecFilter.sprint`, `_load_sprints()`, etc.
- **When** the rename is applied
- **Then** all become `SpecMeta.cycle`, `Cycle` model, `SpecFilter.cycle`, `_load_cycles()`, etc.

### Scenario: Tests updated

- **Given** tests reference sprint in fixtures, assertions, and filter parameters
- **When** the rename is applied
- **Then** all tests pass with the new naming

## Constraints

- Pure rename — no behavioral changes
- Must update: models, config loader, store filter, cache schema, next.py filter, web routes, all tests, config files, docs
- Backwards compatibility for `sprints.yaml` is NOT required (no deployed instances to migrate)

## Verification

- [ ] `sprints.yaml` → `cycles.yaml` with updated keys
- [ ] `Sprint` model → `Cycle` model
- [ ] `SpecMeta.sprint` → `SpecMeta.cycle`
- [ ] `SpecFilter.sprint` → `SpecFilter.cycle`
- [ ] `get_next(..., sprint=)` → `get_next(..., cycle=)`
- [ ] Cache schema uses `cycle` column
- [ ] All tests pass
- [ ] No remaining references to "sprint" in `src/` (grep clean)
- [ ] `docs/spec.md` updated

## References

- DIA-021 (lifecycle automation — uses cycle terminology)

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

## Implementation Notes
