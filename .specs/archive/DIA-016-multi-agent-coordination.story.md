---
id: DIA-016
title: Detect and resolve spec ID collisions after git merge
status: done
type: feature
tags: [core, cli]
business_value: 400
story_points: 5
links:
  blocked_by: [DIA-003, DIA-015]
parent: DIA-012
created: 2026-03-29
updated: 2026-04-03
---

## Description

Detect duplicate spec IDs that arise when branches create specs independently, and provide automated and manual resolution paths.

## Context

When multiple branches (worktrees, different machines) create specs concurrently, they may assign the same ID. Since `next_id()` only sees the current branch, cross-branch collisions are inevitable. The strategy is: best-effort prevention on create, reliable detection on merge, and straightforward resolution via CLI.

## Behavior

### Scenario: Duplicate IDs detected after git merge

- **Given** Branch A created `DIA-021-user-auth.story.md` and Branch B created `DIA-021-api-caching.story.md`
- **When** the branches are merged and `diatagma validate` runs
- **Then** it reports a duplicate ID error listing both files and their slugs

### Scenario: Validate --fix auto-renumbers duplicates

- **Given** two specs share ID `DIA-021` after a merge: `DIA-021-user-auth.story.md` (created earlier) and `DIA-021-api-caching.story.md` (created later)
- **When** `diatagma validate --fix` is run
- **Then** the newer file is assigned the next available ID (e.g., `DIA-022`), its file is renamed to `DIA-022-api-caching.story.md`, the `id` frontmatter is updated, all references across specs are updated, and a summary of changes is printed

### Scenario: Validate --fix with ambiguous references

- **Given** `DIA-021` is duplicated and `DIA-030` has `blocked_by: [DIA-021]`
- **When** `diatagma validate --fix` is run
- **Then** it renumbers the duplicate but flags the ambiguous reference as a warning: "DIA-030 references DIA-021 which was duplicated — verify `blocked_by` still points to the intended spec (now DIA-021-user-auth or DIA-022-api-caching)"

### Scenario: Manual renumber via CLI

- **Given** two specs share ID `DIA-021` after a merge
- **When** `diatagma renumber DIA-021 DIA-022 --file DIA-021-api-caching.story.md` is run
- **Then** the file is renamed, frontmatter updated, and all references pointing at the old file are updated to `DIA-022`

### Scenario: Ambiguous reference during manual renumber

- **Given** `DIA-021` is duplicated and `DIA-030` has `blocked_by: [DIA-021]`
- **When** `diatagma renumber DIA-021 DIA-022 --file DIA-021-api-caching.story.md` is run
- **Then** references that can be resolved (only one file remains with `DIA-021`) are updated automatically; truly ambiguous references are flagged as warnings for manual review

### Scenario: next_id avoids known IDs

- **Given** specs DIA-001 through DIA-021 exist on the current branch
- **When** `diatagma create "New feature"` is run
- **Then** the new spec gets ID `DIA-022`

## Constraints

- No external dependencies — detection and resolution use only the filesystem and existing core modules
- ID collision prevention is best-effort (checks current branch on create); detection + resolution is the safety net for cross-branch collisions
- "Older" file for `--fix` is determined by git commit timestamp, falling back to filesystem mtime

## Requirements

### Detection
- [ ] `detect_duplicate_ids() -> list[DuplicateGroup]` — scan all specs, group by ID, report duplicates with file paths and slugs
- [ ] Integrate duplicate detection into `diatagma validate` (non-zero exit on duplicates)

### Resolution
- [ ] `renumber_spec(old_id, new_id, file_path)` — rename file, update frontmatter `id`, update all references across all spec files
- [ ] Reference update scans all frontmatter fields that can contain IDs: `dependencies`, `blocked_by`, `relates_to`, `supersedes`, `discovered_from`, `parent`
- [ ] When references are ambiguous (multiple files share the ID being renumbered), flag as warnings for manual review
- [ ] `validate --fix` auto-renumbers duplicates: keeps the older file's ID, assigns `next_id()` to the newer one, updates references, and flags ambiguous references as warnings
- [ ] `renumber` CLI command for manual resolution

### Prevention
- [ ] `next_id(prefix)` checks existing files on current branch before assigning (best-effort)

## Verification

- [ ] `validate` detects duplicate IDs and reports both file paths with slugs
- [ ] `validate` exits non-zero when duplicates are found
- [ ] `renumber` updates the file, frontmatter, filename, and all references in other specs
- [ ] `renumber` without `--file` errors when the ID is ambiguous (multiple files)
- [ ] References in `blocked_by`, `relates_to`, `supersedes`, `discovered_from`, `dependencies`, `parent` are all updated
- [ ] `validate --fix` keeps older file's ID, renumbers newer file
- [ ] `validate --fix` flags ambiguous references as warnings
- [ ] `next_id` avoids known IDs on current branch

## References

- [docs/architecture.md](docs/architecture.md)

## Implementation Notes
