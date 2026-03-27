---
id: DIA-013
title: "Epic: Web dashboard — human task interface"
status: pending
type: epic
tags: [web, epic]
business_value: 600
story_points: 21
dependencies: [DIA-011]
assignee: ""
created: 2026-03-27
---

## Description

Build the web dashboard using FastAPI + HTMX + Jinja2 for human task management.

## Context

The dashboard is the human counterpart to the MCP server. It should be fast (HTMX, no SPA build), work for basic operations without JS, and provide rich views for planning and tracking.

## Requirements

- [ ] Kanban board with drag-and-drop status changes (DIA-010)
- [ ] Sortable/filterable task list
- [ ] Task detail view with inline editing
- [ ] Dependency graph visualization
- [ ] Sprint planning view
- [ ] Live search

## Acceptance Criteria

- [ ] All task CRUD operations work through the dashboard
- [ ] Changes made via dashboard are reflected in markdown files immediately
- [ ] External file edits are visible on page refresh
- [ ] Responsive layout works on desktop and tablet

## Implementation Details
