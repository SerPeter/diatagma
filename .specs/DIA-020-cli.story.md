---
id: DIA-020
title: "Build CLI interface for spec management"
status: pending
type: feature
tags: [cli, dx]
business_value: 500
story_points: 5
parent: DIA-012
assignee: ""
created: 2026-03-29
links:
  blocked_by: [DIA-003, DIA-005, DIA-006, DIA-008, DIA-015]
---

## Description

Build a command-line interface that exposes all core spec operations, providing the simplest and most scriptable way to interact with diatagma.

## Context

A CLI is the lowest-friction entry point for developers: no server to start, no browser to open, no MCP client to configure. It's also the most composable — CLI commands pipe into scripts, CI pipelines, git hooks, and shell aliases. The most beloved developer tools (git, ruff, uv) share a pattern: clear subcommands, minimal required arguments, useful defaults, and machine-parseable output when requested. The CLI should feel like a natural extension of the developer's terminal workflow, not a separate "app" to launch.

## Behavior

### Scenario: List ready specs

- **Given** specs exist with various statuses and dependencies
- **When** `diatagma ready` is run
- **Then** it prints unblocked pending specs sorted by priority, one per line

### Scenario: Create a new spec from template

- **Given** the DIA prefix is configured with a story template
- **When** `diatagma create "Implement user authentication"` is run
- **Then** a new spec file is created with the next available ID, the title set, and the story template populated

### Scenario: View spec details

- **Given** DIA-015 exists
- **When** `diatagma show DIA-015` is run
- **Then** the spec's frontmatter and body are printed in a readable format

### Scenario: Update spec status

- **Given** DIA-015 is pending
- **When** `diatagma status DIA-015 in-progress` is run
- **Then** the spec's status is updated in the file and the changelog records the change

### Scenario: Validate all specs

- **Given** some specs have invalid frontmatter or circular dependencies
- **When** `diatagma validate` is run
- **Then** validation errors are printed with file paths and line numbers, and the exit code is non-zero

### Scenario: Machine-readable output

- **Given** the user wants to pipe output into another tool
- **When** `diatagma ready --json` is run
- **Then** output is valid JSON (one object per spec, or a JSON array)

### Scenario: Initialize a new project

- **Given** a repository with no `.specs/` directory
- **When** `diatagma init` is run
- **Then** the `.specs/` directory structure is created with default config, templates, and a `.gitignore` for the cache

## Constraints

- Uses `click` for CLI framework (consistent with Python ecosystem conventions)
- Entry point: `diatagma` (registered via pyproject.toml console_scripts)
- All commands are thin wrappers over core — no business logic in CLI layer
- Human-readable output by default, `--json` flag for machine output
- Exit codes: 0 success, 1 validation errors, 2 usage errors
- Color output via `rich` (respects `NO_COLOR` environment variable)

## Requirements

### Commands
- [ ] `diatagma init` — scaffold `.specs/` directory with config and templates
- [ ] `diatagma create <title> [--type story|epic|spike] [--prefix DIA]` — create spec from template
- [ ] `diatagma show <id>` — display spec details
- [ ] `diatagma list [--status pending] [--tag core] [--type feature]` — filtered spec listing
- [ ] `diatagma ready [--limit N]` — show actionable specs (unblocked, priority-sorted)
- [ ] `diatagma status <id> <new-status>` — update spec status
- [ ] `diatagma edit <id> [--field assignee] <value>` — update frontmatter field
- [ ] `diatagma validate [--fix]` — check all specs for schema violations, dependency cycles, and duplicate IDs. `--fix` auto-resolves fixable issues (renumbers duplicates, etc.)
- [ ] `diatagma renumber <old-id> <new-id> --file <filename>` — rename a spec's ID and update all references across specs
- [ ] `diatagma graph [--format json|dot]` — export dependency graph
- [ ] `diatagma search <query>` — full-text search via FTS5
- [ ] `diatagma agents-md` — generate AGENTS.md (delegates to DIA-017)
- [ ] `diatagma archive-cycle <cycle-name>` — archive completed cycle specs (delegates to DIA-021)
- [ ] `diatagma archive --done` — archive all terminal specs (delegates to DIA-021)
- [ ] `diatagma serve` — start web API server (delegates to DIA-010)
- [ ] `diatagma mcp` — start MCP server (delegates to DIA-009)

### Output & UX
- [ ] `--json` flag on all list/show commands for machine-parseable output
- [ ] Colored output via `rich` (respects `NO_COLOR`)
- [ ] `--quiet` flag to suppress non-essential output (for scripting)
- [ ] Tab completion support (click's built-in shell completion)
- [ ] Helpful error messages with suggestions (e.g., "DIA-099 not found. Did you mean DIA-009?")

## Verification

- [ ] All commands execute successfully with valid input
- [ ] `diatagma validate` catches schema errors and cycles, returns non-zero exit code
- [ ] `diatagma ready` matches MCP `get_ready_specs` output exactly (same core function)
- [ ] `--json` output is valid JSON parseable by `jq`
- [ ] `diatagma init` creates a working project from scratch
- [ ] Tab completion works in bash and zsh
- [ ] `NO_COLOR=1` disables colored output

## References

- [click documentation](https://click.palletsprojects.com/)
- [rich documentation](https://rich.readthedocs.io/)

## Implementation Notes

### Sync architecture (from DIA-018 analysis)

CLI mutations go through `SpecStore.update()` → file write → `SpecWatcher` detects → cache update. Same redundant-but-correct path as MCP. CLI reads should go through the cache for performance. The watcher is optional for CLI (short-lived commands don't benefit from live watching), but if the CLI runs a long-lived mode (e.g., `diatagma watch` or a TUI), start `SpecWatcher` as a background thread to keep the cache fresh.
