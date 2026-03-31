# Roadmap

## Phase 1: Core Library (DIA-011) — Done

**Goal**: A working core that can parse, store, query, rank, and coordinate spec files.

Foundation for everything else. No UI, no MCP — just the shared library that all interfaces depend on. Testable via unit tests and CLI.

- DIA-001: Pydantic models
- DIA-002: Frontmatter parser
- DIA-003: SpecStore CRUD
- DIA-004: SQLite cache
- DIA-005: Dependency graph (networkx DAG)
- DIA-006: Priority scoring (WSJF)
- DIA-007: Changelog
- DIA-008: Config loader
- DIA-014: Typed dependency relationships (blocks, relates_to, supersedes, discovered_from)
- DIA-015: "Get ready specs" deterministic query
- DIA-018: File watcher for live change detection
- DIA-019: Archive with context summaries
- DIA-021: Lifecycle automation (auto-complete parents, completion metadata, cycle archival)
- DIA-023: Rename sprint → cycle, .tasks → .specs

## Phase 2: Agent & CLI Interfaces (DIA-012)

**Goal**: AI agents and developers can discover, claim, and work on specs via MCP tools or CLI commands, with safe multi-agent coordination.

All interfaces are thin wrappers over core. Focus on ergonomic tool/command schemas that minimize token overhead and agent hallucination.

- DIA-020: CLI interface (simplest entry point — no server required)
- DIA-009: FastMCP server with tools, resources, and prompts
- DIA-016: Multi-agent coordination (claim/lock semantics)
- DIA-017: AGENTS.md auto-generation

**Milestone**: `diatagma ready` works from CLI. An AI agent can call `get_ready_specs()` via MCP, claim a spec, and update its status. Two agents can work concurrently without corruption.

## Phase 3: Web Dashboard (DIA-013)

**Goal**: Humans can manage specs through a browser-based dashboard.

Litestar JSON API backend + React/Vite frontend. Keyboard-first UX, sub-100ms response times via SQLite cache.

- DIA-010: Litestar API + React dashboard (kanban, list, detail, graph views)

**Milestone**: Kanban board works, specs editable in browser, changes reflected in markdown files. All primary workflows completable via keyboard.

## Phase 4: Polish & Integration

**Goal**: Production-ready tool with smooth DX for both humans and agents.

- Cycle management
- Dependency graph visualization (React Flow)
- `diatagma init` scaffolding command
- Package publication (PyPI)
