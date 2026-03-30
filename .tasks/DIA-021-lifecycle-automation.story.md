---
id: DIA-021
title: "Implement lifecycle automation: completion metadata, auto-complete parents, reopening guards, batch archival"
status: done
type: story
tags: [core, lifecycle, agents]
business_value: 400
story_points: 8
parent: DIA-011
assignee: ""
created: 2026-03-29
links:
  blocked_by: [DIA-003, DIA-005, DIA-006, DIA-007, DIA-015]
  relates_to: [DIA-019, DIA-023]
---

## Description

Add lifecycle automation to the core: return rich completion metadata when a spec is marked done, auto-complete parent specs when all children finish, guard against adding work to completed epics/cycles, and provide batch archival commands.

## Context

When an agent marks a spec as done, the interaction shouldn't just return "ok." The most productive pattern in agent task tooling is returning contextual metadata on completion — parent progress, newly unblocked work, cycle status — so the agent can immediately decide what to do next without a follow-up query. This saves a round-trip and keeps agents in flow.

Manually tracking epic/parent completion is error-prone and tedious. If all children of an epic are done, the epic should auto-transition. This is table-stakes behavior for hierarchical task systems.

Completed epics and cycles need reopening guards. When a task is added to a done (not archived) epic, the epic should auto-reopen — its "done" state was derived from children, so a new child invalidates it. Archived epics require an explicit `--reopen` flag to override. For cycles: adding a task to a completed cycle is an error — the user must assign to a different cycle or explicitly reopen with `--reopen`.

Post-merge consistency is handled separately (see Constraints) — this spec covers the happy-path lifecycle, not conflict resolution.

## Behavior

### Scenario: Spec marked done returns completion metadata

- **Given** DIA-015 is `in-progress` under parent DIA-011, and DIA-020 has `blocked_by: [DIA-015]`
- **When** DIA-015's status is updated to `done`
- **Then** the response includes a `CompletionContext` with:
  - Parent progress: "4/8 stories in DIA-011 done"
  - Cycle progress: "6/10 specs in Cycle 1 done" (if cycle is set)
  - Newly unblocked: [DIA-020] (specs whose last blocker was just completed)
  - Next ready: top 5 specs from `get_next()` (capped for context efficiency)

### Scenario: Last child completes, parent auto-transitions

- **Given** DIA-011 has 8 child stories, 7 are done, DIA-015 is the last one `in-progress`
- **When** DIA-015 is marked `done`
- **Then** DIA-011 automatically transitions to `done`, the changelog records both transitions, and the completion metadata notes "DIA-011 auto-completed (all children done)"

### Scenario: Auto-complete is recursive

- **Given** DIA-011 is the last pending child of a roadmap phase epic
- **When** DIA-011 auto-completes
- **Then** its parent also auto-completes if all siblings are done (cascades up)

### Scenario: Cancelled children don't block parent completion

- **Given** DIA-011 has 8 children: 7 done, 1 cancelled
- **When** the last non-terminal child is marked done
- **Then** DIA-011 auto-completes (cancelled counts as terminal, same as done)

### Scenario: Task added to done epic — auto-reopen

- **Given** DIA-011 is an epic with status `done` (not archived)
- **When** a new spec is created with `parent: DIA-011`
- **Then** DIA-011's status is set back to `in-progress`, and the changelog records "DIA-011 reopened (new child added)"

### Scenario: Task added to archived epic — error with override

- **Given** DIA-011 is archived in `.tasks/archive/`
- **When** a new spec is created with `parent: DIA-011`
- **Then** an error is returned: "DIA-011 is archived. Use --reopen to unarchive and reopen it."
- **When** `--reopen` is passed
- **Then** DIA-011 is moved back from archive, status set to `in-progress`, changelog records the unarchive

### Scenario: Task added to completed cycle — error

- **Given** "Cycle 1" is complete (all specs terminal)
- **When** a spec is assigned `cycle: "Cycle 1"`
- **Then** an error is returned: "Cycle 'Cycle 1' is complete. Assign to a different cycle or use --reopen to reactivate it."
- **When** `--reopen` is passed
- **Then** the cycle is reopened and the spec is assigned

### Scenario: Cycle archival

- **Given** Cycle 1 has ended, containing 8 specs: 6 done, 1 cancelled, 1 in-progress
- **When** `archive_cycle("Cycle 1")` is called
- **Then** the 7 terminal specs are moved to `.tasks/archive/`, the 1 in-progress spec remains active, and a warning lists the remaining specs

### Scenario: Batch archive all completed specs

- **Given** 5 specs are `done` and 2 are `cancelled` across all cycles
- **When** `archive_done()` is called
- **Then** all 7 terminal specs are moved to `.tasks/archive/`

### Scenario: Completion metadata on non-done status change

- **Given** DIA-015 is `pending`
- **When** DIA-015's status is updated to `in-progress`
- **Then** no completion metadata is returned (only triggers on transition to `done`)

### Scenario: All cycle tasks done — completion signal

- **Given** all specs in "Cycle 1" are terminal
- **When** the last spec is marked `done`
- **Then** `CompletionContext` includes `cycle_complete: True` so the agent knows to look beyond the current cycle

### Scenario: Post-merge inconsistency — done epic with non-done children

- **Given** agent A on branch X marks epic DIA-011 as done (all children were terminal)
- **And** agent B on branch Y adds a new child DIA-025 with `parent: DIA-011` (status: pending)
- **When** the branches are merged and specs are loaded
- **Then** `validate_consistency()` detects DIA-011 is done but has non-terminal child DIA-025
- **And** DIA-011 is auto-reopened to `in-progress` with changelog entry "DIA-011 reopened (non-terminal child DIA-025 detected)"

### Scenario: Post-merge inconsistency — completed cycle with active tasks

- **Given** agent A completes all cycle tasks and marks "Cycle 1" as done
- **And** agent B adds a new spec to "Cycle 1" (status: pending)
- **When** the branches are merged and specs are loaded
- **Then** `validate_consistency()` detects the inconsistency and logs a warning: "Cycle 'Cycle 1' has non-terminal specs but was previously complete"

### Scenario: Consistency validation on store load

- **Given** the spec directory contains inconsistent state (from any source — merge, manual edit, race condition)
- **When** `SpecStore` is initialized or `validate_consistency()` is called explicitly
- **Then** all invariants are checked and auto-corrected where safe (epic reopen), warned where not (cycle state)

## Constraints

- Auto-complete only triggers on transition to `done`, not on other statuses
- Terminal statuses: `done` and `cancelled` — both count as "finished" for parent completion checks
- `auto_complete_parent` setting in `settings.yaml` controls whether auto-complete is active (default: true)
- Completion metadata capped at 5 items for `next_ready` (context efficiency)
- Consistency validation auto-corrects epic state (safe — derived from children) but only warns on cycle state (ambiguous — user may intend the assignment)
- Uses "cycle" terminology (DIA-023 handles the rename, but this spec is written with the target naming)

## Requirements

### Completion Metadata
- [ ] `CompletionContext` model: parent_progress, cycle_progress, cycle_complete, newly_unblocked, next_ready, auto_completed_parents
- [ ] Returned by `update_status()` when new status is `done`
- [ ] `parent_progress`: "{done_count}/{total_count} stories in {parent_id} done"
- [ ] `cycle_progress`: "{done_count}/{total_count} specs in {cycle_name} done" (if cycle set)
- [ ] `cycle_complete`: True when all specs in the cycle are now terminal
- [ ] `newly_unblocked`: specs whose last blocker was the just-completed spec
- [ ] `next_ready`: top 5 from `get_next()` after this completion

### Auto-Complete Parents
- [ ] After marking a spec `done`, check if all siblings under same parent are terminal
- [ ] If so, auto-transition parent to `done` with changelog entry noting "auto-completed"
- [ ] Recurse: check parent's parent, and so on
- [ ] Controlled by `auto_complete_parent` setting (default: true)

### Reopening Guards
- [ ] Adding a child to a done (not archived) epic → auto-reopen epic to `in-progress`
- [ ] Adding a child to an archived epic → error with `--reopen` override
- [ ] Assigning a spec to a completed cycle → error with `--reopen` override
- [ ] All reopens recorded in changelog

### Batch Archival
- [ ] `archive_cycle(cycle_name)` — move all terminal specs in the cycle to archive
- [ ] `archive_done()` — move all terminal specs (regardless of cycle) to archive
- [ ] Both delegate to `move_to_archive()` (DIA-019 summary warning)
- [ ] Non-terminal specs remain in place (log a warning listing them)

### Consistency Validation
- [ ] `validate_consistency()` method on `SpecStore` — checks all lifecycle invariants
- [ ] Done epic with non-terminal children → auto-reopen epic to `in-progress`, log + changelog entry
- [ ] Completed cycle with non-terminal specs → log warning (no auto-correction)
- [ ] Orphaned children (parent ID doesn't exist) → log warning
- [ ] Called on `SpecStore` initialization (or explicitly)
- [ ] Returns list of `ConsistencyIssue` (type, spec_id, message, auto_corrected: bool)

## Verification

- [ ] Marking last child done auto-completes parent
- [ ] Auto-complete cascades up multiple levels
- [ ] Cancelled children count as terminal for parent completion
- [ ] `auto_complete_parent: false` disables the behavior
- [ ] Completion metadata includes correct parent progress fraction
- [ ] Completion metadata lists newly unblocked specs
- [ ] `next_ready` is capped at 5 items
- [ ] `cycle_complete` is True when all cycle specs are terminal
- [ ] Adding child to done epic reopens it
- [ ] Adding child to archived epic errors without `--reopen`
- [ ] Assigning to completed cycle errors without `--reopen`
- [ ] `archive_cycle` moves only terminal specs, leaves active specs with warning
- [ ] `archive_done` works across all cycles
- [ ] Changelog records all auto-transitions, reopens, and archive moves
- [ ] `validate_consistency()` detects done epic with non-terminal children and reopens it
- [ ] `validate_consistency()` warns on completed cycle with active tasks (no auto-correct)
- [ ] `validate_consistency()` warns on orphaned children
- [ ] Returns structured `ConsistencyIssue` list

## References

- [docs/architecture.md](docs/architecture.md)
- DIA-019 (implementation summary / archive warning)
- DIA-023 (sprint → cycle rename)

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

Added `LifecycleEngine` class in new `core/lifecycle.py` module, orchestrating lifecycle transitions across store, graph, and priority layers. `update_status()` returns `CompletionContext` with parent/sprint progress, newly unblocked specs, next ready work, and auto-completed parents. Reopening guards on `create_spec()` protect completed epics and sprints. `validate_consistency()` detects post-merge inconsistencies (done epics with active children, mixed sprint state, orphaned children) with auto-correction for epics.

## Implementation Notes

Lifecycle logic placed in dedicated module rather than expanding store — store stays CRUD, lifecycle is business logic. Graph patched in-memory via `update_node_status()` after mutations to avoid full rebuilds. Sprint naming kept as-is pending DIA-023 rename.
