# Diatagma — Agent Instructions

## What is this?

Spec-driven story coordination for humans and AI agents. Markdown spec files with YAML frontmatter are the source of truth. MCP server + web dashboard are read/write interfaces on top.

## Tech Stack

- **Python 3.12+** (develop on 3.14)
- **uv** for package management
- **FastMCP 3.x** for MCP server ([ADR-001](docs/adr/001-use-fastmcp-over-official-sdk.md))
- **Litestar** for web API backend ([ADR-002](docs/adr/002-litestar-over-fastapi.md))
- **React + Vite** for dashboard frontend ([ADR-003](docs/adr/003-react-vite-frontend.md))
- **networkx** for dependency DAG
- **SQLite** for read cache (`.specs/.cache/tasks.db`)
- **Pydantic 2.x** for all models and validation
- **Ruff** for linting/formatting, **ty** for type checking

## Architecture

```
src/diatagma/
  core/    — shared library (models, parser, store, cache, graph, priority)
  mcp/     — FastMCP server (thin wrapper over core)
  web/     — Litestar JSON API (thin wrapper over core)
frontend/  — React dashboard (Vite SPA)
```

**core/ is the only layer that touches the filesystem.** MCP and web import from core, never from each other. See [docs/architecture.md](docs/architecture.md) for full diagrams and data flows.

## Terminology

- **Spec** = any markdown file in `.specs/` (the unit of work)
- **Story** = a spec from the user's perspective (`.story.md`)
- **Epic** = a spec grouping related stories (`.epic.md`)
- **Spike** = a research spec producing ADRs/research docs (`.spike.md`)

## Spec System (Dogfooding)

This repo uses its own `.specs/` directory with the `DIA` prefix.

- Config: `.specs/config/`
- Templates: `.specs/config/templates/` (story.md, epic.md, spike.md)
- Roadmap: `.specs/ROADMAP.md`
- Changelog: `.specs/changelog.md`
- Active specs: `.specs/DIA-*.{story,epic,spike}.md`
- Backlog: `.specs/backlog/`
- Archive: `.specs/archive/`

Use `diatagma next --json` to find the highest-priority actionable work. See the `/diatagma` skill for full CLI reference and workflow.

## Documentation

- `docs/spec.md` — product specification
- `docs/architecture.md` — system architecture, diagrams, flows
- `docs/adr/NNN-slug.md` — Architecture Decision Records
- `docs/research/YYMMDD_slug.md` — research documents from spikes

**ADRs and research docs are sources of truth for decisions.** Always check relevant ADRs before revisiting a settled choice.

## Workflow

```
write spec → derive tests from behavior scenarios → implement → verify against spec
```

For architectural decisions:
```
spike → research doc + ADR → informed stories reference these
```

## Commands

### Development

```bash
uv sync                            # Install dependencies
uv run pytest                      # Run tests
uv run ruff check --fix .          # Lint
uv run ruff format .               # Format
uv run ty check                    # Type check
uv run pre-commit run --all-files  # All pre-commit hooks
```

### Diatagma CLI

```bash
uv run diatagma next               # Show priority-sorted actionable specs
uv run diatagma show DIA-017       # Display spec details
uv run diatagma list               # List all active specs
uv run diatagma list --status pending  # Filter by status
uv run diatagma status DIA-017 in-progress  # Update spec status
uv run diatagma create "Title"     # Create a new spec
uv run diatagma validate           # Check for inconsistencies
uv run diatagma graph              # Export dependency graph (JSON)
uv run diatagma init --skill       # Install Claude Code skill
uv run diatagma init --update      # Regenerate skill after changes
```

All commands support `--json` for machine-readable output and `--specs-dir` to override the `.specs/` location.

## Conventions

- Conventional commits (enforced by pre-commit hook)
- src layout with hatchling build backend
- All models in `core/models.py`, all config in `core/config.py`
- Tests mirror source structure: `tests/test_<module>.py`
- No database — the filesystem is the database, SQLite is just a cache
- Spec files use typed extensions: `.story.md`, `.epic.md`, `.spike.md`
