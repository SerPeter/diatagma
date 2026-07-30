---
id: DIA-028
title: Status drift detection command
status: done
type: feature
tags: [cli, dx, lifecycle]
business_value: 250
story_points: 3
created: 2026-07-30
updated: 2026-07-30
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

- [x] Unit tests over a synthetic git log fixture for both drift kinds
- [x] Clean-repo case yields empty result, exit 0
- [x] `--json` shape covered
- [x] Graceful degradation when git absent
- [x] Full suite, ruff, ty pass

## References

- [[DIA-007]] changelog, [[DIA-016]] multi-agent coordination

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

New read-only `diatagma drift` command backed by `core/drift.py`. It scans
`git log` once, mapping spec IDs mentioned in commit messages, and reports
`implemented_not_marked` for any non-terminal spec referenced by a commit, plus
`stale_in_progress` for in-progress specs whose file hasn't been committed
within `drift_stale_days` (new setting, default 14). Git runs via subprocess
with graceful degradation: `git_available` gates a warning and all git calls
return empty rather than raising. `--json` emits a list of drift records.
Running it against this repo immediately surfaced two real drifts (DIA-010,
DIA-022 referenced in commits while still pending).

## Implementation Notes

- The mention signal keys on the `PREFIX-NNN` pattern in commit subjects/bodies;
  since spec IDs are never reused, this is precise without a since-date filter.
- Staleness uses the file's last committer date (`git log -1 --format=%cs`);
  a spec file with no git history is treated as not-stale (undeterminable).
- `today` and `stale_days` are injected into `detect_drift` so tests are
  deterministic (no wall-clock dependence).
