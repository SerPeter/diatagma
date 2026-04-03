---
id: DIA-024
title: Auto-generate ROADMAP.md from current spec state
status: done
type: feature
tags: [cli, dx]
business_value: 200
story_points: 3
links:
  blocked_by: [DIA-008, DIA-020]
parent: DIA-012
created: 2026-04-02
updated: 2026-04-03
---

## Description

Auto-generate `ROADMAP.md` from the current state of spec files so the roadmap always reflects reality instead of requiring manual upkeep.

## Context

The roadmap is currently hand-maintained. As specs are added, completed, or reorganized, the roadmap drifts out of sync. Since all the information already lives in spec frontmatter (status, parent epics, IDs), the roadmap can be derived automatically — same pattern as DIA-017 (AGENTS.md generation).

The generated roadmap should group specs by phase (epic), show completion status, and preserve any hand-written prose sections (phase goals, milestones) while updating the spec listings.

## Behavior

### Scenario: Generate roadmap from scratch

- **Given** a diatagma project with epics and child specs
- **When** `diatagma roadmap` is run
- **Then** a `ROADMAP.md` is written to `.specs/ROADMAP.md` with phases derived from epics, each listing their child specs with current status indicators

### Scenario: Reflect spec completion

- **Given** specs DIA-001 through DIA-008 have status `done`
- **When** `diatagma roadmap` is run
- **Then** those specs appear with a done indicator (e.g., ~~strikethrough~~ or checkmark) and the parent epic shows a completion summary (e.g., "8/12 done")

### Scenario: Preserve user-maintained prose

- **Given** ROADMAP.md contains hand-written phase goals and milestone descriptions outside of auto-generated markers
- **When** `diatagma roadmap` is run after a spec status changes
- **Then** the auto-generated spec listings are updated but all user prose outside `<!-- diatagma:roadmap:start -->` / `<!-- diatagma:roadmap:end -->` markers is preserved

### Scenario: Specs without a parent epic

- **Given** specs exist that have no `parent` field or whose parent is not an epic
- **When** `diatagma roadmap` is run
- **Then** those specs appear under an "Ungrouped" section at the end

### Scenario: Deterministic output

- **Given** a set of specs in a known state
- **When** `diatagma roadmap` is run twice without changes
- **Then** the output is identical both times

### Scenario: JSON output

- **Given** a diatagma project with specs
- **When** `diatagma roadmap --json` is run
- **Then** a JSON structure is emitted with phases, their specs, and completion stats — suitable for dashboard consumption

## Constraints

- Must be deterministic: same spec state always produces same output
- Must not overwrite user prose outside the fenced markers
- Spec ordering within a phase: by ID (numeric sort)
- Epic ordering: by the order they appear in an existing ROADMAP.md (if present), otherwise by ID
- Should reuse the same marker-fence pattern as DIA-017 (`<!-- diatagma:...:start -->` / `<!-- diatagma:...:end -->`)
- Core function in `core/`, CLI command as thin wrapper

## Verification

- [ ] Generated ROADMAP.md accurately reflects all active and archived spec statuses
- [ ] Epics with all children done are marked as complete
- [ ] User prose outside markers survives regeneration
- [ ] Deterministic: same input produces identical output
- [ ] `--json` flag emits valid JSON with phase/spec/status structure
- [ ] Specs without a parent epic appear in "Ungrouped" section
- [ ] CLI command `diatagma roadmap` works end-to-end

## References

- DIA-017: AGENTS.md auto-generation (same marker-fence pattern)
- `.specs/ROADMAP.md`: current hand-maintained roadmap

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

Core module `core/roadmap.py` generates ROADMAP.md with three fenced sections: meta table (total/active/archived/backlog counts), epics table (pending/active/done per epic), and current/next cycle spec lists. CLI command `diatagma roadmap` writes or updates the file, preserving user prose outside marker fences. Supports `--json` for structured output. Cycle detection derives current/next from `cycles.yaml` date ranges.

## Implementation Notes

- Marker fence pattern: `<!-- diatagma:TAG:start -->` / `<!-- diatagma:TAG:end -->` with regex replacement
- `update_roadmap_file()` preserves prose outside fences; falls back to full regeneration if no fences found
- `_current_cycle()` matches by date range, falls back to most recent past cycle
- Epics appear in both the epics table and the cycle list (with `(epic)` suffix)
- 22 tests covering cycle detection, generation with/without cycles, prose preservation, JSON output, and CLI integration
