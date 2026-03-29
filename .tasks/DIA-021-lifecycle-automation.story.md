---
id: DIA-021
title: "Implement lifecycle automation: auto-complete parents, completion metadata, sprint archival"
status: pending
type: story
tags: [core, lifecycle, agents]
business_value: 400
story_points: 5
parent: DIA-011
dependencies: [DIA-003, DIA-005, DIA-006, DIA-007, DIA-015]
blocked_by: []
relates_to: [DIA-019]
assignee: ""
created: 2026-03-29
---

## Description

Add lifecycle automation to the core: auto-complete parent specs when all children finish, return rich completion metadata when a spec is marked done, and provide sprint/batch archival commands.

## Context

When an agent marks a spec as done, the interaction shouldn't just return "ok." The most productive pattern observed in agent task tooling is returning contextual metadata on completion — parent progress, newly unblocked work, sprint status — so the agent can immediately decide what to do next without a follow-up query. This saves a round-trip and keeps agents in flow.

Similarly, manually tracking epic/parent completion is error-prone and tedious. If all children of an epic are done, the epic should auto-transition. This is table-stakes behavior that users expect from any hierarchical task system but is frequently missing in file-based tools.

Sprint archival (moving all done/cancelled specs to archive at sprint end) keeps the active directory clean and the working set focused.

## Behavior

### Scenario: Spec marked done returns completion metadata

- **Given** DIA-015 is `in-progress` under parent DIA-011, and DIA-020 has `blocked_by: [DIA-015]`
- **When** DIA-015's status is updated to `done`
- **Then** the response includes a `CompletionContext` with:
  - Parent progress: "4/8 stories in DIA-011 done"
  - Sprint progress: "6/10 specs in Sprint 1 done" (if sprint is set)
  - Newly unblocked: [DIA-020] (specs that became actionable because of this completion)
  - Next ready: top 5 specs from `get_ready_specs()` (capped for context efficiency)

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

### Scenario: Sprint archival

- **Given** Sprint 1 has ended, containing 8 specs: 6 done, 1 cancelled, 1 in-progress
- **When** `diatagma archive-sprint "Sprint 1"` is run
- **Then** the 6 done and 1 cancelled specs are moved to `.tasks/archive/`, the 1 in-progress spec remains active, and archive summaries are generated per DIA-019

### Scenario: Batch archive all completed specs

- **Given** 5 specs are `done` and 2 are `cancelled` across all sprints
- **When** `diatagma archive --done` is run
- **Then** all 7 terminal specs are moved to `.tasks/archive/` with summaries generated

### Scenario: Completion metadata on non-done status change

- **Given** DIA-015 is `pending`
- **When** DIA-015's status is updated to `in-progress`
- **Then** no completion metadata is returned (only triggers on transition to `done`)

## Constraints

- Auto-complete only triggers on transition to `done`, not on other statuses
- Terminal statuses: `done` and `cancelled` — both count as "finished" for parent completion checks
- `auto_complete_parent` setting in `settings.yaml` controls whether this behavior is active (default: true)
- Completion metadata capped at 5 items for `next_ready` (context efficiency)
- Archive commands delegate to DIA-019 for summary generation

## Requirements

### Completion Metadata
- [ ] `CompletionContext` model: parent_progress, sprint_progress, newly_unblocked, next_ready, auto_completed_parents
- [ ] Returned by `update_status()` when new status is `done`
- [ ] `parent_progress`: "{done_count}/{total_count} stories in {parent_id} done"
- [ ] `sprint_progress`: "{done_count}/{total_count} specs in {sprint_name} done" (if sprint set)
- [ ] `newly_unblocked`: specs whose last blocker was the just-completed spec
- [ ] `next_ready`: top 5 from `get_ready_specs()` after this completion

### Auto-Complete Parents
- [ ] After marking a spec `done`, check if all siblings under same parent are terminal (`done` or `cancelled`)
- [ ] If so, auto-transition parent to `done` with changelog entry noting "auto-completed"
- [ ] Recurse: check parent's parent, and so on
- [ ] Controlled by `auto_complete_parent` setting (default: true)

### Sprint Archival
- [ ] `archive_sprint(sprint_name)` — move all terminal specs in the sprint to archive
- [ ] `archive_done()` — move all terminal specs (regardless of sprint) to archive
- [ ] Both delegate to `move_to_archive()` which generates summaries (DIA-019)
- [ ] Non-terminal specs remain in place (log a warning listing them)

### CLI Commands
- [ ] `diatagma archive-sprint <sprint-name>` — archive completed sprint specs
- [ ] `diatagma archive --done` — archive all terminal specs

## Verification

- [ ] Marking last child done auto-completes parent
- [ ] Auto-complete cascades up multiple levels
- [ ] Cancelled children count as terminal for parent completion
- [ ] `auto_complete_parent: false` disables the behavior
- [ ] Completion metadata includes correct parent progress fraction
- [ ] Completion metadata lists newly unblocked specs
- [ ] `next_ready` is capped at 5 items
- [ ] `archive-sprint` moves only terminal specs, leaves in-progress specs
- [ ] `archive --done` works across all sprints
- [ ] Changelog records all auto-transitions and archive moves

## References

## Implementation Notes
