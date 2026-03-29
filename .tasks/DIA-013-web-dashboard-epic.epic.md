---
id: DIA-013
title: "Epic: Web dashboard — human task interface"
status: pending
type: epic
tags: [web, epic]
business_value: 600
story_points: 21
dependencies: [DIA-011, DIA-020]
assignee: ""
created: 2026-03-27
updated: 2026-03-29
---

## Vision

Humans can manage specs through a browser-based dashboard with kanban, list, detail, and graph views — all keyboard-navigable and fast.

## Context

The dashboard is the human counterpart to the MCP server and CLI. It uses Litestar for the JSON API backend and React + Vite for the frontend SPA, as decided in ADR-002 and ADR-003. The web server is started via `diatagma serve` (CLI subcommand from DIA-020). The API is a thin wrapper over core — no business logic in handlers.

## Stories

- [ ] DIA-022: Dashboard UX design (wireframes + interaction spec)
- [ ] DIA-010: Litestar API + React dashboard (kanban, list, detail, graph views)

## Behavior

### Scenario: User manages specs through the browser

- **Given** `diatagma serve` is running
- **When** the user opens the dashboard
- **Then** they can view, create, edit, and transition specs through kanban, list, and detail views

## Constraints

- Backend: Litestar JSON API (thin wrapper over core)
- Frontend: React + Vite SPA
- Keyboard-first UX, sub-100ms response times via SQLite cache

## Verification

- [ ] All child stories are done
- [ ] All spec CRUD operations work through the dashboard
- [ ] Changes made via dashboard are reflected in markdown files immediately
- [ ] External file edits are visible on page refresh
- [ ] All primary workflows completable via keyboard
- [ ] Responsive layout works on desktop and tablet

## References

- [ADR-002: Litestar over FastAPI](docs/adr/002-litestar-over-fastapi.md)
- [ADR-003: React + Vite frontend](docs/adr/003-react-vite-frontend.md)
