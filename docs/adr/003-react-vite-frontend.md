# ADR-003: Use React with Vite for the dashboard frontend

## Status

Accepted

## Context

The dashboard needs rich interactivity: kanban drag-and-drop, dependency graph visualization, inline editing, live search, and data tables with filtering/sorting. Three options were considered:

1. **HTMX + Jinja2** — server-rendered with sprinkled interactivity
2. **React + Vite** — component-based SPA with JSON API backend
3. **Angular** — full-featured framework with opinionated structure

The primary developer has limited frontend experience. The tool needs to start simple but support increasing complexity over time.

## Decision

Use **React with Vite** as the frontend framework.

## Consequences

### Positive

- Battle-tested component libraries for every dashboard need: `@dnd-kit/core` (kanban), `react-flow`/`@xyflow` (dependency graph), `@tanstack/table` (data tables)
- Vite provides zero-config dev experience with fast HMR — low friction to start
- Massive ecosystem and learning resources — easier to find solutions
- Clean separation: Litestar serves JSON, React consumes it — each layer has one job
- Transferable skill for future tools in the agentic development suite

### Negative

- Requires Node.js toolchain alongside Python — two ecosystems to maintain
- Initial learning curve for React hooks and state management
- Heavier than HTMX for simple CRUD pages — but the dashboard isn't simple CRUD

### Neutral

- The React app lives in `frontend/`, fully decoupled from the Python backend
- In production, `diatagma serve` serves the React build as static files — single process deployment
- TypeScript types can be generated from the Litestar OpenAPI spec

## References

- Vite: https://vite.dev
- React: https://react.dev
- @dnd-kit: https://dndkit.com
- React Flow: https://reactflow.dev
- TanStack Table: https://tanstack.com/table
