# diatagma

Spec-driven story coordination for humans and AI agents.

**Markdown spec files are the source of truth.** Diatagma provides an MCP server for AI agents and a web dashboard for humans — both read and write the same plain markdown files with YAML frontmatter.

## Features

- **Spec-driven workflow** — write spec → derive tests from behavior → implement → verify
- **Plain markdown specs** — prefixed, numbered files in a `.tasks/` directory with structured YAML frontmatter
- **Typed file extensions** — `.story.md`, `.epic.md`, `.spike.md` for instant identification
- **MCP server** — AI agents create, query, claim, and update stories via typed tools
- **Web dashboard** — kanban board, filterable list, dependency graph, inline editing (React + Litestar)
- **Dependency DAG** — networkx-powered blocking/unblocking with cycle detection
- **Priority scoring** — WSJF-style composite ranking (business value, story points, blockers, age, due dates)
- **No database** — filesystem is the source of truth, SQLite is just a read cache
- **Changelog** — append-only audit trail of all mutations with agent attribution
- **ADR + research docs** — architectural decisions and spike findings as traceable knowledge
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

## Spec File Format

```markdown
---
id: CORE-042
title: "Implement retry logic for API calls"
status: in-progress
type: feature
tags: [api, resilience]
business_value: 300
story_points: 5
parent: CORE-040
sprint: "Sprint 3"
assignee: claude-agent-abc
due_date: 2026-04-15
dependencies: [CORE-041]
created: 2026-03-27
---

## Description

Add exponential backoff retry logic to all external API calls.

## Context

Production incidents showed cascading failures when upstream APIs had transient errors.
See [ADR-005](docs/adr/005-retry-strategy.md) for the chosen approach.

## Behavior

### Scenario: Transient API failure recovers

- **Given** an external API call that fails with a 503
- **When** the retry logic is triggered
- **Then** it retries up to 3 times with exponential backoff and jitter

### Scenario: Persistent failure trips circuit breaker

- **Given** 5 consecutive API failures
- **When** the next call is attempted
- **Then** the circuit breaker opens and fails fast for 30 seconds

## Constraints

- Max 3 retries with jitter
- Circuit breaker timeout: 30s

## Verification

- [ ] All external API calls use retry with exponential backoff
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Retry metrics exposed via logging

## References

- [ADR-005: Retry Strategy](docs/adr/005-retry-strategy.md)
- [Research: Circuit Breaker Patterns](docs/research/260320_circuit-breaker-patterns.md)

## Implementation Notes
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
│       ├── story.md        # Story body template
│       ├── epic.md         # Epic body template
│       └── spike.md        # Spike/research template
├── roadmap.md              # Phased roadmap with narrative
├── changelog.md            # Append-only mutation log
├── backlog/                # Not yet scheduled
├── archive/                # Completed/cancelled
├── CORE-042-retry-logic.story.md
├── CORE-040-api-hardening.epic.md
└── ...

docs/
├── spec.md                 # Product specification
├── architecture.md         # System architecture + diagrams
├── adr/                    # Architecture Decision Records
│   ├── 001-slug.md
│   └── template.md
└── research/               # Date-prefixed research docs
    └── YYMMDD_slug.md
```

## License

Apache 2.0
