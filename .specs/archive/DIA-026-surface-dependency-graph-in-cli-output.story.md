---
id: DIA-026
title: Surface dependency graph in CLI output
status: done
type: feature
tags: [cli, dx, graph]
business_value: 200
story_points: 3
created: 2026-07-30
updated: 2026-07-30
---

## Description

`list` marks blocked specs, `show` displays computed blocked-state and what a spec unblocks, and starting a blocked spec emits a notice naming the unfinished blockers.

## Context

`SpecGraph` already computes blockers, dependents, and unblocked sets, but the CLI only uses it to filter `next` and detect cycles. `show` prints the declared `blocked_by` IDs without saying whether the spec is *currently* blocked, and nothing shows what finishing a spec would unblock. The graph does the work; the CLI hides it. Reuses the notice channel from [[DIA-025]].

## Behavior

### Scenario: blocked marker in list

- **Given** DIA-002 is blocked by pending DIA-001
- **When** `diatagma list` runs
- **Then** DIA-002's row carries a marker naming the blockers, e.g. `[blocked by DIA-001]`

### Scenario: show displays computed dependency state

- **Given** DIA-002 blocked by pending DIA-001, and DIA-003 declares `blocked_by: [DIA-002]`
- **When** `diatagma show DIA-002` runs
- **Then** output shows `Blocked:  DIA-001 (pending)` and `Unblocks: DIA-003`

### Scenario: notice when starting a blocked spec

- **Given** DIA-002 is blocked by non-terminal DIA-001
- **When** `diatagma status DIA-002 in-progress` runs
- **Then** the update succeeds AND a `blocked_start` notice lists the unfinished blockers

### Scenario: no notice when blockers terminal

- **Given** DIA-002's only blocker DIA-001 is done
- **When** `diatagma status DIA-002 in-progress` runs
- **Then** no `blocked_start` notice is produced

## Constraints

- Warn, never block — parallel work on a blocked spec is sometimes deliberate.
- Graph is already built per invocation; no extra scans in `list`.
- JSON output may gain fields but must not change existing ones.

## Verification

- [x] Lifecycle/CLI tests for each scenario
- [x] `blocked_start` notice reuses the DIA-025 channel
- [x] Full suite, ruff, ty pass

## References

- [[DIA-005]] dependency graph, [[DIA-025]] notice channel

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

`list` now builds the graph and appends a `[blocked by ...]` marker to any row
with non-terminal blockers. `show` builds the graph too: `print_spec_detail`
gained optional `blocker_statuses` (renders `Blocked: DIA-001 (pending)`) and
`dependents` (an `Unblocks:` line from `graph.get_dependents`). Starting a spec
with active blockers emits a `blocked_start` notice via the DIA-025 channel.
Archived/done blockers are filtered out everywhere, so only live blockers show.

## Implementation Notes

- Graph and status map are built once per command and reused for epic progress,
  blocked markers, and children — no extra filesystem scans beyond the existing
  refresh.
- Blocker status uses the full spec set (`include_archive=True`) so an archived,
  done blocker correctly reads as non-blocking.
- Warn-never-block preserved: `status in-progress` on a blocked spec succeeds.
