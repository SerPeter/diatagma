# Architecture

## Overview

Diatagma is a spec-driven story coordination tool. Markdown files with YAML frontmatter are the single source of truth. Two interfaces — an MCP server (for AI agents) and a web dashboard (for humans) — provide read/write access to the same spec files through a shared core library.

```
┌─────────────────────────────────────────────────────┐
│                    Consumers                         │
│  ┌──────────────┐              ┌──────────────────┐ │
│  │  AI Agents   │              │  Human (Browser)  │ │
│  └──────┬───────┘              └────────┬─────────┘ │
│         │ MCP Protocol                  │ HTTP/WS    │
│  ┌──────▼───────┐              ┌────────▼─────────┐ │
│  │  FastMCP 3.x │              │  React Dashboard  │ │
│  │  (stdio/SSE) │              │  (Vite SPA)       │ │
│  └──────┬───────┘              └────────┬─────────┘ │
│         │                               │ JSON API   │
│         │                      ┌────────▼─────────┐ │
│         │                      │  Litestar API     │ │
│         │                      │  (Python)         │ │
│         │                      └────────┬─────────┘ │
│  ┌──────▼───────────────────────────────▼─────────┐ │
│  │              Core Library                       │ │
│  │  ┌─────────┐ ┌──────┐ ┌───────┐ ┌───────────┐ │ │
│  │  │ Models  │ │Parser│ │ Store │ │ Changelog │ │ │
│  │  ├─────────┤ ├──────┤ ├───────┤ ├───────────┤ │ │
│  │  │ Schema  │ │Config│ │ Cache │ │  Search   │ │ │
│  │  ├─────────┤ ├──────┤ ├───────┤ ├───────────┤ │ │
│  │  │  Graph  │ │      │ │       │ │ Priority  │ │ │
│  │  └─────────┘ └──────┘ └───────┘ └───────────┘ │ │
│  └──────────────────┬─────────────────────────────┘ │
│                     │ Filesystem I/O                  │
│  ┌──────────────────▼─────────────────────────────┐ │
│  │              .tasks/ Directory                   │ │
│  │  ┌──────────┐ ┌────────┐ ┌──────┐ ┌─────────┐ │ │
│  │  │*.story.md│ │*.epic.md│ │config│ │changelog│ │ │
│  │  │*.spike.md│ │backlog/ │ │      │ │         │ │ │
│  │  │          │ │archive/ │ │      │ │         │ │ │
│  │  └──────────┘ └────────┘ └──────┘ └─────────┘ │ │
│  │  ┌──────────────────────────────────────────┐  │ │
│  │  │ .cache/tasks.db (SQLite, gitignored)     │  │ │
│  │  └──────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Key Principle: Core Owns the Filesystem

**Only `core/` touches spec files.** MCP and web are thin wrappers that call core functions. This means:

- Both interfaces always see the same state
- Logic changes happen in one place
- Core is testable without MCP or HTTP overhead
- Manual file edits are valid — core re-parses on access

## Data Flow

### Write path (create/update)

```
Agent/User → MCP tool or API endpoint
  → core.store.create() or .update()
    → core.parser.write_spec_file()     # write to filesystem
    → core.changelog.append_entry()     # log the mutation
    → core.cache.invalidate()           # mark cache stale
```

### Read path (list/query)

```
Agent/User → MCP tool or API endpoint
  → core.store.list(filters, sort_by)
    → core.cache.query()               # try cache first
    → if stale: core.parser.parse_spec_file()  # re-parse
    → core.graph.is_blocked()           # compute DAG status
    → core.priority.compute_priority()  # rank results
```

### Priority computation

```
core.priority.compute_priority(spec, graph, config)
  = (business_value × w_bv + time_criticality × w_tc + risk_reduction × w_rr)
    / max(story_points, 1)
    + unblocks_bonus × graph.get_dependents(spec_id).count
    + age_bonus × days_since_created
    + due_date_urgency_bonus
```

## Technology Choices

| Component | Technology | ADR |
|---|---|---|
| MCP server | FastMCP 3.x | [ADR-001](adr/001-use-fastmcp-over-official-sdk.md) |
| Web API | Litestar | [ADR-002](adr/002-litestar-over-fastapi.md) |
| Frontend | React + Vite | [ADR-003](adr/003-react-vite-frontend.md) |
| Dependency graph | networkx | — |
| Read cache | SQLite (FTS5) | — |
| Models | Pydantic 2.x | — |
| Spec format | Markdown + YAML frontmatter | — |

## Directory Layout

```
diatagma/
├── src/diatagma/
│   ├── core/          # Shared library — filesystem is the database
│   ├── mcp/           # FastMCP server (thin wrapper over core)
│   └── web/           # Litestar JSON API (thin wrapper over core)
├── frontend/          # React dashboard (Vite)
├── tests/             # Mirrors src/ structure
├── docs/
│   ├── adr/           # Architecture Decision Records
│   ├── research/      # Date-prefixed research documents
│   ├── spec.md        # Product specification
│   └── architecture.md  # This file
└── .tasks/            # Dogfooding — diatagma's own specs
```
