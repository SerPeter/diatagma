---
id: DIA-010
title: "Build web dashboard with Litestar API and React frontend"
status: pending
type: story
tags: [web, dashboard, ui]
business_value: 400
story_points: 13
parent: DIA-013
assignee: ""
created: 2026-03-27
updated: 2026-03-29
links:
  blocked_by: [DIA-003, DIA-005, DIA-008, DIA-014, DIA-015, DIA-022]
---

## Description

Build the web dashboard using Litestar for the JSON API backend and React + Vite for the frontend SPA, providing kanban board, task list, detail views, and dependency graph visualization.

## Context

The dashboard is the human interface for spec management. Research into developer tool UX consistently shows that sub-50ms response times (via local-first or optimistic UI) and keyboard-first navigation are the two highest-impact patterns for power user adoption. Tools that neglect keyboard shortcuts or feel sluggish lose users to CLI alternatives. The Litestar + React stack was chosen per ADR-002 and ADR-003.

## Behavior

### Scenario: User views kanban board

- **Given** specs exist in various statuses
- **When** the user opens the dashboard
- **Then** specs are displayed as cards in status columns, ordered by priority score

### Scenario: User drags spec to new status

- **Given** a spec card on the kanban board
- **When** the user drags it to a different status column
- **Then** the spec's markdown file is updated with the new status and the changelog records the change

### Scenario: User navigates entirely by keyboard

- **Given** the dashboard is open
- **When** the user presses `/` to focus search, arrow keys to navigate, `Enter` to open, `Esc` to close
- **Then** all primary workflows are completable without touching the mouse

### Scenario: External file change is reflected

- **Given** a spec file is modified outside the dashboard (by an agent or text editor)
- **When** the user refreshes or the file watcher triggers
- **Then** the dashboard shows the updated content

## Constraints

- Backend is a thin wrapper over core — no business logic in API handlers
- Frontend communicates exclusively via JSON API (no server-side rendering)
- Keyboard shortcuts must not conflict with browser defaults
- Dashboard must work on desktop and tablet viewports

## Requirements

### Backend (Litestar JSON API)
- [ ] REST endpoints: GET/POST/PUT specs, GET graph, GET ready, POST search
- [ ] Cursor-based pagination on list endpoints
- [ ] WebSocket endpoint for live update notifications (when file watcher is available)
- [ ] Proper HTTP error responses with structured error bodies

### Frontend (React + Vite)
- [ ] Kanban board view with drag-and-drop status changes
- [ ] Sortable/filterable list view
- [ ] Spec detail view with inline frontmatter editing
- [ ] Dependency graph visualization (React Flow or d3-force)
- [ ] Search with live results
- [ ] Keyboard shortcut system (`/` search, `n` new, `k/j` navigate, `Enter` open)
- [ ] Responsive layout (desktop + tablet)

## Verification

- [ ] All spec CRUD operations work through the dashboard
- [ ] Kanban drag-and-drop updates the markdown file on disk
- [ ] Filters and sort persist across navigation
- [ ] All primary workflows completable via keyboard only
- [ ] Dashboard reflects external file changes on refresh
- [ ] API response times <100ms for all list operations (with cache)

## References

- [ADR-002: Litestar over FastAPI](docs/adr/002-litestar-over-fastapi.md)
- [ADR-003: React + Vite frontend](docs/adr/003-react-vite-frontend.md)

## Implementation Notes
