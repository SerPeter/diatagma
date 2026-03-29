---
id: DIA-001
title: "Define Pydantic models for task metadata and configuration"
status: done
type: feature
tags: [core, models]
business_value: 500
story_points: 5
parent: DIA-011
assignee: ""
created: 2026-03-27
---

## Description

Define the canonical Pydantic models that represent task frontmatter, task body sections, and configuration structures.

## Context

Every other module depends on these models — parser serializes to/from them, store returns them, cache indexes them, MCP and web expose them. Getting the shape right first prevents churn downstream.

## Requirements

- [ ] `TaskMeta` model: id, title, status, type, tags, business_value, story_points, epic, sprint, assignee, due_date, dependencies, blocked_by, related_to, parent, created, updated
- [ ] `TaskBody` model: description, context, requirements, acceptance_criteria, implementation_details (all optional strings)
- [ ] `Task` model: TaskMeta + TaskBody + file_path + computed fields (priority_score, is_blocked)
- [ ] Config models: `Settings`, `PrefixDef`, `SchemaConfig`, `PriorityConfig`, `Sprint`, `HooksConfig`
- [ ] All models use strict validation, sensible defaults, and clear docstrings

## Acceptance Criteria

- [ ] All models importable from `diatagma.core.models`
- [ ] TaskMeta validates id format (PREFIX-NNN pattern)
- [ ] business_value constrained to [-1000, 1000]
- [ ] story_points constrained to Fibonacci values [1, 2, 3, 5, 8, 13, 21]
- [ ] Status constrained to configured enum values
- [ ] Unit tests pass with valid and invalid data

## Implementation Details
