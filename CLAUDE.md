# Diatagma — Project Instructions

## What is this?

File-based task coordination for humans and AI agents. Markdown files with YAML frontmatter are the source of truth. MCP server + web dashboard are read/write interfaces on top.

## Tech Stack

- **Python 3.12+** (develop on 3.14)
- **uv** for package management
- **FastMCP 3.x** for MCP server
- **FastAPI + HTMX + Jinja2** for web dashboard
- **networkx** for dependency DAG
- **SQLite** for read cache (`.tasks/.cache/tasks.db`)
- **Pydantic 2.x** for all models and validation
- **Ruff** for linting/formatting, **ty** for type checking

## Architecture

```
src/diatagma/
  core/    — shared library (models, parser, store, cache, graph, priority)
  mcp/     — FastMCP server (thin wrapper over core)
  web/     — FastAPI dashboard (thin wrapper over core)
```

**core/ is the only layer that touches the filesystem.** MCP and web import from core, never from each other.

## Task System (Dogfooding)

This repo uses its own `.tasks/` directory. Tasks use the `DIA` prefix.

- Config: `.tasks/config/`
- Templates: `.tasks/config/templates/`
- Changelog: `.tasks/changelog.md`
- Active tasks: `.tasks/DIA-*.md`
- Backlog: `.tasks/backlog/`
- Archive: `.tasks/archive/`

## Commands

```bash
uv sync                          # Install dependencies
uv run pytest                    # Run tests
uv run ruff check --fix .        # Lint
uv run ruff format .             # Format
uv run ty check                  # Type check
uv run pre-commit run --all-files  # All pre-commit hooks
uv run diatagma serve            # Start web dashboard
uv run diatagma mcp              # Start MCP server
```

## Conventions

- Conventional commits (enforced by pre-commit hook)
- src layout with hatchling build backend
- All models in `core/models.py`, all config in `core/config.py`
- Tests mirror source structure: `tests/test_<module>.py`
- No database — the filesystem is the database, SQLite is just a cache
