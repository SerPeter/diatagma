# Roadmap

## Phase 1: Core Library (DIA-011)

**Goal**: A working core that can parse, store, query, and rank spec files.

Foundation for everything else. No UI, no MCP — just the shared library that both will depend on. Testable via unit tests and CLI.

- DIA-001: Pydantic models
- DIA-002: Frontmatter parser
- DIA-003: SpecStore CRUD
- DIA-004: SQLite cache
- DIA-005: Dependency graph (networkx DAG)
- DIA-006: Priority scoring (WSJF)
- DIA-007: Changelog
- DIA-008: Config loader

**Milestone**: `diatagma validate` works, all core tests pass.

## Phase 2: MCP Server (DIA-012)

**Goal**: AI agents can discover, claim, and work on specs via MCP tools.

Thin wrapper over core. Focus on ergonomic tool schemas that minimize agent hallucination. Agents should be able to complete a full workflow: discover → claim → work → update → complete.

- DIA-009: FastMCP server with full tool suite

**Milestone**: An AI agent can run `get_next_story()`, claim it, and update its status.

## Phase 3: Web Dashboard (DIA-013)

**Goal**: Humans can manage specs through a browser-based dashboard.

React frontend consuming the Litestar JSON API. Start with the essentials (list view, detail view, basic kanban), then add rich views.

- DIA-010: Litestar API + React dashboard

**Milestone**: Kanban board works, specs editable in browser, changes reflected in markdown files.

## Phase 4: Polish & Integration

**Goal**: Production-ready tool with smooth DX for both humans and agents.

- Sprint management and velocity tracking
- Dependency graph visualization (React Flow)
- File watcher for live updates
- `diatagma init` scaffolding command
- Package publication (PyPI + npm)

## Future

- Multi-project support (multiple .tasks/ roots)
- GitHub/Linear integration (sync specs ↔ issues)
- Collaborative editing (WebSocket live cursors)
- AI-powered spec writing assistant (suggest behavior scenarios)
