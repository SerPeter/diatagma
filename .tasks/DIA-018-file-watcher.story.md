---
id: DIA-018
title: "Implement file watcher for live spec change detection"
status: pending
type: feature
tags: [core, watch, performance]
business_value: 300
story_points: 5
parent: DIA-011
assignee: ""
created: 2026-03-29
links:
  blocked_by: [DIA-003, DIA-004]
---

## Description

Build a file watcher that detects changes to spec files in `.tasks/` and triggers cache invalidation and optional notifications.

## Context

Both the MCP server and web dashboard need to reflect external file changes. Without a watcher, agents see stale data after another agent or human edits a file, and the web dashboard requires manual refresh. Stale state from missing file-change detection is a top-three complaint category in agent task management tools — agents make decisions based on outdated information, leading to duplicate work or blocked-task confusion. The watcher should invalidate the SQLite cache and optionally push notifications to connected WebSocket clients.

## Behavior

### Scenario: Spec file modified externally

- **Given** the file watcher is running and DIA-001.story.md exists in the cache
- **When** a user edits DIA-001.story.md in their text editor
- **Then** the cache entry for DIA-001 is invalidated within 2 seconds

### Scenario: New spec file created

- **Given** the file watcher is running
- **When** a new file DIA-030.story.md is created in `.tasks/`
- **Then** the file is parsed and added to the cache, and connected clients are notified

### Scenario: Spec file deleted

- **Given** the file watcher is running and DIA-005.story.md exists
- **When** the file is deleted from `.tasks/`
- **Then** the cache entry is removed and connected clients are notified

### Scenario: Batch changes (e.g., git checkout)

- **Given** the file watcher is running
- **When** a git checkout changes 20 spec files simultaneously
- **Then** changes are debounced and processed as a single batch cache rebuild (not 20 individual invalidations)

## Constraints

- Must use `watchfiles` (Rust-based, cross-platform) — not `watchdog` (slower, more platform issues)
- Debounce window: 500ms (configurable) to handle batch operations
- Watcher runs as optional background thread, not a separate process
- Must handle `.tasks/` subdirectories (backlog/, archive/)
- Must not watch `.tasks/.cache/` (would cause feedback loops)

## Requirements

- [ ] `SpecWatcher` class that monitors `.tasks/` recursively for `.md` file changes
- [ ] Debounced change batching (500ms default window)
- [ ] Cache invalidation callback: invalidate specific entries or trigger full rebuild
- [ ] WebSocket notification callback: push change events to connected dashboard clients
- [ ] Ignore patterns: `.cache/`, `.tmp` files, non-`.md` files
- [ ] Graceful start/stop lifecycle (context manager)
- [ ] Cross-platform: Windows, macOS, Linux

## Verification

- [ ] File modification triggers cache invalidation within debounce window
- [ ] File creation adds new entry to cache
- [ ] File deletion removes entry from cache
- [ ] Batch changes (20+ files) are debounced into single rebuild
- [ ] `.cache/` directory changes are ignored
- [ ] Watcher starts and stops cleanly without resource leaks

## References

- [watchfiles documentation](https://watchfiles.helpmanual.io/)

## Implementation Notes

Implemented as `SpecWatcher` in `core/watcher.py`. Uses `watchfiles.watch()` in a daemon thread with `stop_event` for clean shutdown. Built-in debounce at 500ms (configurable). `SpecFileFilter` subclasses `DefaultFilter` to pass only `.md` files, rejecting `.cache/`, `.tmp`, and inherited ignores (`.git`, etc.). Callbacks receive `list[SpecChangeEvent]` domain events (not raw watchfiles tuples) with `change_type`, `path`, and pre-extracted `spec_id`. Two factory functions: `make_cache_callback` (individual put/invalidate below threshold, full `cache.rebuild()` above) and `make_notify_callback` (pass-through for future WebSocket wiring). Context manager protocol supported. Watcher is self-contained — not yet wired into SpecStore or web layer.
