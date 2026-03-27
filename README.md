# diatagma

File-based task coordination for humans and AI agents.

**Markdown files are the source of truth.** Diatagma provides an MCP server for AI agents and a web dashboard for humans — both read and write the same plain markdown task files with YAML frontmatter.

## Features

- **Plain markdown tasks** — prefixed, numbered files in a `.tasks/` directory with structured YAML frontmatter
- **MCP server** — AI agents create, query, claim, and update tasks via typed tools
- **Web dashboard** — kanban board, filterable list, dependency graph, inline editing
- **Dependency DAG** — networkx-powered blocking/unblocking with cycle detection
- **Priority scoring** — WSJF-style composite ranking (business value, story points, blockers, age, due dates)
- **No database** — filesystem is the source of truth, SQLite is just a read cache
- **Changelog** — append-only audit trail of all mutations with agent attribution
- **Configurable** — templates, schemas, priority weights, sprints, lifecycle hooks

## Quick Start

```bash
# Install
uv add diatagma

# Initialize a .tasks/ directory in your project
diatagma init

# Start the web dashboard
diatagma serve

# Start the MCP server (for AI agent integration)
diatagma mcp
```

## Task File Format

```markdown
---
id: CORE-042
title: "Implement retry logic for API calls"
status: in-progress
type: feature
tags: [api, resilience]
business_value: 300
story_points: 5
epic: api-hardening
sprint: "Sprint 3"
assignee: claude-agent-abc
due_date: 2026-04-15
dependencies: [CORE-040, CORE-041]
created: 2026-03-27
---

## Description

Add exponential backoff retry logic to all external API calls.

## Context

Production incidents showed cascading failures when upstream APIs had transient errors.

## Requirements

- [ ] As a service operator, I want API calls to retry with backoff so that transient errors don't cause cascading failures.

## Acceptance Criteria

- [ ] All external API calls use retry with exponential backoff
- [ ] Max 3 retries with jitter
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Retry metrics exposed via logging

## Implementation Details
```

## Directory Structure

```
.tasks/
├── .gitignore              # Always ignores .cache/
├── .cache/                 # SQLite read cache (gitignored)
├── config/
│   ├── settings.yaml       # Tool behavior settings
│   ├── prefixes.yaml       # Prefix definitions
│   ├── schema.yaml         # Frontmatter validation rules
│   ├── priority.yaml       # WSJF scoring weights
│   ├── sprints.yaml        # Sprint boundaries
│   ├── hooks.yaml          # Lifecycle hooks
│   └── templates/
│       ├── default.md      # Default task body template
│       └── spike.md        # Research/exploration template
├── changelog.md            # Append-only mutation log
├── backlog/                # Not yet scheduled
├── archive/                # Completed/cancelled
├── CORE-042-retry-logic.md # Active tasks
└── ...
```

## License

Apache 2.0
