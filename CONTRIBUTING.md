# Contributing to Diatagma

Thanks for your interest in contributing! This guide covers the essentials.

## Prerequisites

- **Python 3.12+** (we develop on 3.14)
- **[uv](https://docs.astral.sh/uv/)** for package management
- **Node.js 20+** for the frontend dashboard

## Setup

```bash
git clone https://github.com/SerPeter/diatagma.git
cd diatagma
uv sync --group dev
uv run pre-commit install --install-hooks
```

## Development

```bash
uv run pytest                      # Run tests
uv run ruff check --fix .          # Lint
uv run ruff format .               # Format
uv run ty check                    # Type check
uv run pre-commit run --all-files  # All pre-commit hooks
```

## Code Quality

- **Linting & formatting**: [Ruff](https://docs.astral.sh/ruff/)
- **Type checking**: [ty](https://github.com/astral-sh/ty)
- **Commit messages**: [Conventional Commits](https://www.conventionalcommits.org/) — enforced by pre-commit hook

Valid prefixes: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

## Architecture

```
src/diatagma/
  core/    — shared library (models, parser, store, cache, graph, priority)
  mcp/     — FastMCP server (thin wrapper over core)
  web/     — Litestar JSON API (thin wrapper over core)
frontend/  — React dashboard (Vite SPA)
```

**core/ is the only layer that touches the filesystem.** MCP and web import from core, never from each other.

## Pull Requests

1. Fork the repo and create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass: `uv run pre-commit run --all-files`
4. Open a PR against `main`

## License

By contributing, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
