---
id: DIA-007
title: "Implement append-only changelog tracking"
status: done
type: feature
tags: [core, changelog, audit]
business_value: 200
story_points: 3
parent: DIA-011
assignee: ""
created: 2026-03-27
links:
  blocked_by: [DIA-001]
---

## Description

Build the changelog module that records all task mutations as structured, append-only entries in .specs/changelog.md.

## Context

The changelog provides at-a-glance audit trail without needing git blame. Both human and agent changes are logged with agent ID attribution.

## Requirements

- [ ] `append_entry(task_id, field, old, new, agent_id)` — single field change
- [ ] `append_creation(task_id, agent_id)` — new task
- [ ] `read_entries(since: date | None) → list[ChangelogEntry]`
- [ ] Entries grouped by date with `## YYYY-MM-DD` headers
- [ ] One line per change, git-friendly format

## Acceptance Criteria

- [ ] Entries are appended atomically (no partial writes on crash)
- [ ] Reading changelog returns parsed ChangelogEntry objects
- [ ] Date grouping is correct across timezone boundaries

## Implementation Details
