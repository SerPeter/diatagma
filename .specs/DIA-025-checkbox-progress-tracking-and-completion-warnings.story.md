---
id: DIA-025
title: Checkbox progress tracking and completion warnings
status: pending
type: feature
tags: [cli, dx, lifecycle]
business_value: 350
story_points: 5
created: 2026-07-30
---

## Description

Status changes carry structured **notices** (surfaced in both CLI and MCP), and the first producer warns when a spec is marked `done` while its verification checkboxes are still unchecked.

## Context

Two gaps compound here:

1. **No feedback on incomplete work.** The Verification section's `- [ ]` boxes are the "done" contract, but nothing reads them — `status done` closes a spec with every box empty and says nothing. Agents skip boxes silently.
2. **MCP never sees lifecycle feedback.** `update_spec`/`claim_spec` call `store.update()` directly (`mcp/tools.py:273,292`), bypassing `LifecycleEngine`. Even the existing `CompletionContext` (parent progress, auto-completed parents) never reaches MCP agents, and there is no channel at all for non-terminal transitions.

This story builds the shared **notice channel** that [[DIA-026]] and [[DIA-031]] plug into, routes MCP status mutations through the lifecycle engine so notices actually reach agents, and ships checkboxes as the first producer.

## Behavior

### Scenario: checkbox counts parsed from body

- **Given** a spec whose body has 3 unchecked and 2 checked items
- **When** the spec is parsed
- **Then** checkbox progress reports 2 checked of 5 total

### Scenario: template placeholder ignored

- **Given** a spec whose Verification section holds only the template stub `- [ ] ...`
- **When** the spec is parsed
- **Then** checkbox progress reports 0 total

### Scenario: notice on done with unchecked boxes

- **Given** a spec with unchecked, non-placeholder checkboxes
- **When** its status is set to `done` (via CLI **or** MCP)
- **Then** the update succeeds AND a notice `unchecked_boxes` is returned, e.g. `DIA-042: 3 of 5 checkboxes unchecked`

### Scenario: no notice when boxes complete

- **Given** a spec whose boxes are all checked (or which has none)
- **When** status is set to `done`
- **Then** no `unchecked_boxes` notice is produced

### Scenario: MCP status change routes through lifecycle

- **Given** an agent calls `update_spec(status=...)` over MCP
- **When** the change is applied
- **Then** it flows through `LifecycleEngine.update_status` and the tool response includes any notices and completion context (previously discarded)

### Scenario: progress shown in show

- **Given** a spec with checkboxes
- **When** `diatagma show DIA-042` runs
- **Then** the detail view includes a `Boxes: 2/5` line

### Scenario: validate flags done specs with unchecked boxes

- **Given** an active spec with status `done` and unchecked boxes
- **When** `diatagma validate` runs
- **Then** a warn-level issue `done_with_unchecked_boxes` is reported (not auto-corrected); archived specs are exempt

## Constraints

- **Warn, never block** — `status done` still succeeds; agents read notices, hard blocks punish placeholder-only specs.
- Notice is a structured model (`kind`, `spec_id`, `message`, optional `suggested_command`), not a bare string, so CLI and MCP can render consistently.
- `StatusUpdateResult.notices` is populated on **all** transitions, not just terminal ones.
- Checkbox parsing must not alter body round-tripping.

## Verification

- [ ] Unit tests for checkbox extraction (counts, `[X]` uppercase, nested lists, placeholder exclusion)
- [ ] Notice model + `StatusUpdateResult.notices` populated on done transition
- [ ] MCP `update_spec`/`claim_spec` route through lifecycle and return notices
- [ ] CLI `status` prints notices; `show` prints `Boxes:` line
- [ ] `validate` yields `done_with_unchecked_boxes` for active specs only
- [ ] Full suite, ruff, ty pass

## References

- [[DIA-021]] lifecycle automation, [[DIA-026]] blocked-start notices, [[DIA-031]] epic notices

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

## Implementation Notes
