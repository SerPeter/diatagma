---
id: DIA-002
title: "Implement markdown+YAML frontmatter parser"
status: done
type: feature
tags: [core, parser]
business_value: 500
story_points: 5
parent: DIA-011
dependencies: [DIA-001]
assignee: ""
created: 2026-03-27
---

## Description

Build the parser that converts between on-disk markdown files and in-memory Task models.

## Context

This is the serialization boundary — it must round-trip cleanly (read a file, write it back, get the same content). Uses python-frontmatter for YAML extraction and PyYAML for serialization.

## Requirements

- [ ] `parse_task_file(path) → Task` — read a .md file and return a fully populated Task
- [ ] `write_task_file(task, path)` — serialize a Task back to markdown with YAML frontmatter
- [ ] `parse_frontmatter(text) → TaskMeta` — extract just the metadata
- [ ] `render_task(task) → str` — produce the full markdown string
- [ ] Handle missing optional fields gracefully
- [ ] Preserve body content that doesn't match known sections

## Acceptance Criteria

- [ ] Round-trip test: parse → render → parse produces identical Task
- [ ] Handles files with no body (frontmatter only)
- [ ] Handles files with extra unknown frontmatter fields (preserves them)
- [ ] Raises clear errors for malformed YAML

## Implementation Details
