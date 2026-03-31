---
id: DIA-004
title: "Implement SQLite read cache with mtime invalidation"
status: done
type: feature
tags: [core, cache, performance]
business_value: 300
story_points: 5
parent: DIA-011
assignee: ""
created: 2026-03-27
links:
  blocked_by: [DIA-001, DIA-003]
---

## Description

Build a SQLite-backed read cache at .specs/.cache/tasks.db that accelerates listing, filtering, and sorting.

## Context

Parsing YAML frontmatter on every request doesn't scale. The cache stores pre-parsed metadata with mtime-based invalidation. It's always gitignored and rebuilt on startup if missing.

## Requirements

- [ ] SQLite DB at .specs/.cache/tasks.db
- [ ] Table: tasks (all frontmatter fields + file mtime + file path)
- [ ] FTS5 virtual table for full-text search across body content
- [ ] `put(task)` / `get(task_id)` / `query(filters, sort_by)`
- [ ] mtime check on get — return None if stale, triggering re-parse
- [ ] `rebuild(tasks)` — full cache rebuild from parsed task list
- [ ] Cache version constant — bump to force rebuild on schema changes

## Acceptance Criteria

- [ ] Cache miss triggers re-parse from filesystem (transparent to caller)
- [ ] Deleting tasks.db and restarting works without data loss
- [ ] FTS5 search returns relevant results
- [ ] Concurrent reads don't block (WAL mode)

## Implementation Details
