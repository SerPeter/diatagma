---
id: DIA-008
title: "Implement configuration loader from .tasks/config/"
status: done
type: feature
tags: [core, config]
business_value: 400
story_points: 3
parent: DIA-011
assignee: ""
created: 2026-03-27
links:
  blocked_by: [DIA-001]
---

## Description

Build the config module that loads and validates all YAML configuration files from .tasks/config/ into typed Pydantic models.

## Context

Configuration drives behavior across the tool — statuses, prefixes, templates, priority weights, sprint boundaries. It must be loaded once and shared by both MCP and web.

## Requirements

- [ ] Load settings.yaml, prefixes.yaml, schema.yaml, priority.yaml, sprints.yaml, hooks.yaml
- [ ] Load templates from config/templates/*.md
- [ ] Typed access via `DiatagmaConfig` class
- [ ] Sensible defaults when config files are missing
- [ ] Validation errors on malformed config

## Acceptance Criteria

- [ ] Missing config files produce warnings but don't crash
- [ ] Invalid YAML produces clear error messages with file path
- [ ] Templates are resolved by prefix first, then by type, then default

## Implementation Details
