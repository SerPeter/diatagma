---
id: DIA-016
title: "Implement multi-agent coordination with claim/lock semantics"
status: pending
type: feature
tags: [core, agents, concurrency]
business_value: 400
story_points: 8
parent: DIA-012
assignee: ""
created: 2026-03-29
links:
  blocked_by: [DIA-003, DIA-015]
---

## Description

Build the coordination layer that allows multiple AI agents to work on specs concurrently without data corruption or duplicate work.

## Context

Race conditions on concurrent file writes are the most frequently reported data corruption bug in file-based task management tools. The pattern: two agents read the same JSON file, both modify it, one write overwrites the other. Solutions range from file-level locking (simplest, sufficient for single-machine) to database transactions (overkill for filesystem-first tools). Since diatagma's source of truth is the filesystem, the approach should be file-level locking with atomic writes and a claim registry that lives alongside the specs. Over-engineering this with a full database layer introduces more bugs than it solves — multiple tools have learned this the hard way.

## Behavior

### Scenario: Agent claims a spec

- **Given** DIA-015 is ready and unclaimed
- **When** Agent A calls `claim_spec("DIA-015", agent_id="agent-a")`
- **Then** DIA-015's status becomes `in-progress`, assignee is set to `agent-a`, and the claim is recorded with a timestamp

### Scenario: Second agent cannot claim same spec

- **Given** DIA-015 is claimed by Agent A
- **When** Agent B calls `claim_spec("DIA-015", agent_id="agent-b")`
- **Then** the call returns an error indicating the spec is already claimed by another agent

### Scenario: Claim expires after timeout

- **Given** Agent A claimed DIA-015 30 minutes ago and hasn't sent a heartbeat
- **When** any agent calls `get_ready_specs()`
- **Then** DIA-015 appears as ready (claim expired), and any agent can re-claim it

### Scenario: Agent releases a claim

- **Given** Agent A has claimed DIA-015
- **When** Agent A calls `release_spec("DIA-015", agent_id="agent-a")`
- **Then** the claim is removed and the spec returns to pending status

### Scenario: Concurrent file writes are safe

- **Given** two agents attempt to update different specs simultaneously
- **When** both write operations execute
- **Then** both succeed without corruption (each spec is a separate file)

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

## Constraints

- File-level locking only — no external lock server or database for coordination
- Claim state stored in `.tasks/.cache/claims.json` (gitignored, ephemeral)
- Claim timeout configurable via `settings.yaml` (`claim_timeout_minutes`)
- Must work on single machine with multiple agent processes; distributed multi-machine coordination is out of scope
- Atomic writes: write to temp file, then rename (prevents partial writes on crash)
- ID collision prevention is best-effort (check current branch on create); detection + resolution is the safety net for cross-branch collisions

## Requirements

### Claim/Lock Semantics
- [ ] `claim_spec(spec_id, agent_id) -> ClaimResult` — atomic claim with conflict detection
- [ ] `release_spec(spec_id, agent_id) -> bool` — release only if caller owns the claim
- [ ] `heartbeat(spec_id, agent_id)` — extend claim timeout
- [ ] `get_claims() -> dict[str, Claim]` — current claim state
- [ ] Claims registry at `.tasks/.cache/claims.json` with file locking
- [ ] Expired claim cleanup on every read (lazy expiration)

### Safe File I/O
- [ ] Atomic file writes for all spec mutations (write to `.tmp`, rename)
- [ ] File-level locking via `fcntl`/`msvcrt` for write operations on individual spec files

### Git Merge Collision Handling
- [ ] `detect_duplicate_ids() -> list[DuplicateGroup]` — scan all specs, group by ID, report duplicates with file paths and slugs
- [ ] Integrate duplicate detection into `diatagma validate` (non-zero exit on duplicates)
- [ ] `renumber_spec(old_id, new_id, file_path)` — rename file, update frontmatter `id`, update all references across all spec files
- [ ] Reference update scans all frontmatter fields that can contain IDs: `dependencies`, `blocked_by`, `relates_to`, `supersedes`, `discovered_from`, `parent`
- [ ] When references are ambiguous (multiple files share the ID being renumbered), require explicit `--file` flag to disambiguate which spec is being renumbered
- [ ] `validate --fix` auto-renumbers duplicates: keeps the older file's ID, assigns `next_id()` to the newer one, updates references, and flags ambiguous references as warnings
- [ ] `next_id(prefix)` checks existing files on current branch before assigning (best-effort collision prevention)

## Verification

### Claims
- [ ] Two agents claiming the same spec: first succeeds, second gets conflict error
- [ ] Expired claims are cleaned up and spec becomes claimable
- [ ] Heartbeat extends timeout correctly
- [ ] Claims file corruption (e.g., invalid JSON) triggers rebuild, not crash

### File Safety
- [ ] Atomic writes: kill process mid-write, file is not corrupted
- [ ] Concurrent writes to different specs succeed without interference

### ID Collision Handling
- [ ] `validate` detects duplicate IDs and reports both file paths with slugs
- [ ] `renumber` updates the file, frontmatter, filename, and all references in other specs
- [ ] `renumber` refuses to run without `--file` when the ID is ambiguous (multiple files)
- [ ] References in `blocked_by`, `relates_to`, `supersedes`, `discovered_from`, `dependencies`, `parent` are all updated
- [ ] `next_id` avoids known IDs on current branch (best-effort prevention)

## References

- [docs/architecture.md](docs/architecture.md)

## Implementation Notes
