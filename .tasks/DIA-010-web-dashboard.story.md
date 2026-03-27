---
id: DIA-010
title: "Build web dashboard with kanban board and task management"
status: pending
type: feature
tags: [web, dashboard, ui]
business_value: 400
story_points: 13
parent: DIA-013
dependencies: [DIA-003, DIA-005, DIA-008]
assignee: ""
created: 2026-03-27
---

## Description

Build the web dashboard using FastAPI + HTMX + Jinja2, providing kanban board, task list, detail views, and dependency graph visualization.

## Context

The dashboard is the human interface for task management. It should be snappy (HTMX, no SPA), work without JavaScript for basic operations, and provide rich views for planning and tracking.

## Requirements

- [ ] Kanban board view with drag-and-drop status changes
- [ ] Sortable/filterable task list view
- [ ] Task detail view with inline editing
- [ ] Dependency graph visualization (d3-force or vis.js)
- [ ] Search with live results
- [ ] Responsive layout

## Acceptance Criteria

- [ ] All task CRUD operations work through the dashboard
- [ ] Kanban drag-and-drop updates task status in the markdown file
- [ ] Filters persist across page navigation
- [ ] Dashboard reflects external file changes on refresh

## Implementation Details
