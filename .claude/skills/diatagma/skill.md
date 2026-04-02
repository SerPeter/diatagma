---
name: diatagma
description: Spec-driven story coordination — find work, claim specs, update status via CLI
---

# Diatagma CLI Reference

Diatagma manages work as markdown spec files with YAML frontmatter in a `.specs/` directory.
Use the CLI commands below to interact with specs. Always prefer `--json` for machine-readable output.

Check `references/user-preferences.md` for project-specific conventions and preferences.


## Project Configuration

**Prefixes:**
- `DIA` — Diatagma core tool development

**Statuses:** `pending`, `blocked`, `in-progress`, `in-review`, `done`, `cancelled`
**Types:** `story`, `epic`, `spike`, `bug`
**Story points:** 1, 2, 3, 5, 8, 13, 21

## Commands

### `diatagma archive [--done]`
Archive completed specs.

### `diatagma archive-cycle <cycle_name>`
Archive all terminal specs in a cycle.

### `diatagma create <title> [--type <value> | --prefix <value>]`
Create a new spec from template.

### `diatagma edit <spec_id> <value> [--field <value>]`
Update a single frontmatter field.

### `diatagma graph [--format <value>]`
Export the dependency graph.

### `diatagma init [--prefix <value> | --name <value> | --skill | --update | --agents-md]`
Scaffold a .specs/ directory in the current project.

### `diatagma list [--status <value> | --tag <value> | --type <value> | --sort <value> | --reverse]`
List specs with optional filters.

### `diatagma mcp`
Start the MCP server (not yet implemented - see DIA-009).

### `diatagma next [--limit <value> | --tag <value> | --type <value> | --cycle <value>]`
Show next actionable specs sorted by priority.

### `diatagma serve`
Start the web API server (not yet implemented - see DIA-010).

### `diatagma show <spec_id>`
Display spec details.

### `diatagma status <spec_id> <new_status> [--archive]`
Update a spec's status.

### `diatagma validate`
Check all specs for schema violations, dependency cycles, and inconsistencies.

**Global options:** `--specs-dir <path>`, `--json`, `--quiet`, `--no-color`

## Workflow

The standard agent workflow for completing work:

1. **Find ready work:** `diatagma next --json` returns priority-sorted specs with no unresolved blockers
2. **Read the spec:** `diatagma show <id>` to understand requirements and acceptance criteria
3. **Claim it:** `diatagma status <id> in-progress` to signal you're working on it
4. **Do the work:** implement what the spec describes
5. **Mark review:** `diatagma status <id> in-review` when ready for review
6. **Complete:** `diatagma status <id> done` when accepted

## Tips

- Use `diatagma list --status pending` to see all unstarted work
- Use `diatagma validate` to check for broken dependencies or schema issues
- Use `diatagma next --type bug` to focus on bugs only
- All commands support `--json` for structured output
- Use `diatagma edit <id> --field assignee <name>` to claim ownership
