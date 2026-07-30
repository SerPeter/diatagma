---
id: DIA-029
title: Archive command status guard
status: pending
type: feature
tags: [cli, dx, lifecycle]
business_value: 150
story_points: 2
created: 2026-07-30
---

## Description

`diatagma archive DIA-042` archives a single spec but guards on its status — refusing (or warning on) a non-terminal spec — and `status --archive` warns instead of silently doing nothing when the target isn't terminal.

## Context

Today `archive` only operates in bulk (`--done`, `--parent`, `--cycle`) and the per-spec path doesn't exist; `status --archive` silently skips archiving if the status isn't terminal (`spec.py:181`). Agents expect `archive DIA-042` to work and expect to be told when an archive is a no-op. This adds the single-spec command with a status guard and makes the skip visible.

## Behavior

### Scenario: archive a terminal spec

- **Given** `DIA-042` has status `done`
- **When** `diatagma archive DIA-042` runs
- **Then** the spec moves to `archive/` and success is reported

### Scenario: guard a non-terminal spec

- **Given** `DIA-042` has status `in-progress`
- **When** `diatagma archive DIA-042` runs
- **Then** it refuses with a clear message and non-zero exit, unless `--force` is passed

### Scenario: force archive

- **Given** `DIA-042` is non-terminal
- **When** `diatagma archive DIA-042 --force` runs
- **Then** it archives anyway, with a warning

### Scenario: status --archive on non-terminal warns

- **Given** a `status DIA-042 in-progress --archive` invocation
- **When** it runs
- **Then** the status updates AND a warning states the archive was skipped because the status is non-terminal (no more silent no-op)

## Constraints

- Preserve existing bulk `archive --done/--parent/--cycle` behavior unchanged.
- `move_to_archive` already warns on a missing Implementation Summary; keep that.
- Single-spec archive shares the lifecycle path — no direct store poking from the CLI.

## Verification

- [ ] CLI tests: terminal archives, non-terminal refused, `--force` overrides
- [ ] `status --archive` warning on non-terminal spec
- [ ] Bulk archive regression untouched
- [ ] Full suite, ruff, ty pass

## References

- [[DIA-019]] archive summaries, [[DIA-021]] lifecycle automation, [[DIA-031]] epic archive propagation

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

## Implementation Notes
