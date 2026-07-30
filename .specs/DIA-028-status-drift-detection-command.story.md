---
id: DIA-028
title: Status drift detection command
status: pending
type: feature
tags: [cli, dx, lifecycle]
business_value: 250
story_points: 3
created: 2026-07-30
---

## Description

`diatagma drift` reports specs whose recorded status disagrees with reality — implementation committed while the spec is still `pending`/`in-progress`, and specs stuck `in-progress` with no recent activity.

## Context

Agents forget to run `diatagma status ... done` after committing (the AGENTS.md workflow step is skipped constantly). The spec files then lie about the state of the project. Git history is the ground truth for "was this worked on"; drift detection cross-references it against frontmatter so the lie surfaces on demand instead of festering.

## Behavior

### Scenario: committed-but-not-done drift

- **Given** commits since the spec's `created` date mention `DIA-042` in message or touch its files, and `DIA-042` status is `pending` or `in-progress`
- **When** `diatagma drift` runs
- **Then** `DIA-042` is reported as `implemented_not_marked` with the referencing commit shorthands

### Scenario: stale in-progress

- **Given** `DIA-042` is `in-progress` and its file's last git commit is older than the staleness threshold (default 14 days)
- **When** `diatagma drift` runs
- **Then** `DIA-042` is reported as `stale_in_progress` with the age

### Scenario: clean repo reports nothing

- **Given** every spec's status agrees with git history
- **When** `diatagma drift` runs
- **Then** it reports no drift and exits 0

### Scenario: json output

- **Given** any repo state
- **When** `diatagma drift --json` runs
- **Then** a machine-readable list of drift records is printed

## Constraints

- Read-only: `drift` never mutates specs — it reports. (An agent decides what to do.)
- Runs `git` via subprocess; if the repo is unavailable, degrade to staleness-only with a warning, don't crash.
- Spec-ID references matched by the `PREFIX-NNN` pattern in commit subjects/bodies plus changed-file path scan.
- Threshold configurable via a settings field (`drift_stale_days`, default 14).

## Verification

- [ ] Unit tests over a synthetic git log fixture for both drift kinds
- [ ] Clean-repo case yields empty result, exit 0
- [ ] `--json` shape covered
- [ ] Graceful degradation when git absent
- [ ] Full suite, ruff, ty pass

## References

- [[DIA-007]] changelog, [[DIA-016]] multi-agent coordination

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

## Implementation Notes
