---
id: DIA-003
title: "Implement TaskStore CRUD over filesystem"
status: done
type: feature
tags: [core, store]
business_value: 500
story_points: 8
parent: DIA-011
assignee: ""
created: 2026-03-27
links:
  blocked_by: [DIA-001, DIA-002]
---

## Description

Build the TaskStore class that provides CRUD operations over the .specs/ directory, using the parser for file I/O.

## Context

This is the source-of-truth layer. Both MCP and web call through here. It handles file discovery, ID generation, directory management (active/backlog/archive), and coordinates with the cache.

## Requirements

- [ ] `list(filters, sort_by)` — discover and return tasks from all directories
- [ ] `get(task_id)` — find and parse a single task by ID
- [ ] `create(prefix, title, template, **meta)` — generate next ID, write file from template
- [ ] `update(task_id, **changes)` — modify frontmatter and/or body, write back
- [ ] `move_to_backlog(task_id)` / `move_to_archive(task_id)` — move files between directories
- [ ] `next_id(prefix)` — scan existing files to determine next sequential number
- [ ] Log all mutations to changelog

## Acceptance Criteria

- [ ] Creating a task produces a valid markdown file with correct frontmatter
- [ ] ID auto-increment works correctly (DIA-001, DIA-002, ... DIA-999, DIA-1000)
- [ ] Moving tasks between directories preserves file content
- [ ] Concurrent access doesn't corrupt files (file-level locking)
- [ ] All mutations appear in changelog.md

## Implementation Details
