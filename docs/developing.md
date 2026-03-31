# Developing

## Prerequisites

- Python 3.12+ (developed on 3.14)
- [uv](https://docs.astral.sh/uv/) for package management

## Setup

```bash
uv sync          # Install dependencies
```

## Commands

```bash
uv run pytest                      # Run tests
uv run ruff check --fix .          # Lint
uv run ruff format .               # Format
uv run ty check                    # Type check
uv run pre-commit run --all-files  # All pre-commit hooks
uv run diatagma serve              # Start web API server
uv run diatagma mcp                # Start MCP server
```

## Known Issues

### Concurrent pytest on Windows

Running multiple `uv run pytest` processes simultaneously on Windows can cause all of them to hang indefinitely. This has been observed when an AI agent spawns several test runs as background tasks — the processes compete for OS-level file handles and never complete.

**Symptoms**: `uv run pytest` hangs during initialization (before any tests run). Even `pytest --co` (collect-only) blocks.

**Root cause**: Multiple python/pytest processes contending for Windows file handles. The exact lock has not been identified — SQLite WAL, `.pytest_cache`, temp directory cleanup, and `watchfiles` threads have all been ruled out individually. The hang appears to be an emergent effect of many processes competing simultaneously.

**Fix**: Kill all zombie python processes, then retry:

```powershell
Get-Process python* | Stop-Process -Force
```

**Prevention**: Only run one `uv run pytest` at a time. If a test run goes to background or appears stuck, wait for it to finish or kill it before starting another.
