# Diatagma — Product Specification

## Overview

Spec-driven story coordination tool with both an MCP server (for AI agents) and a web dashboard (for humans), tracking work as plain markdown spec files in a `.specs/` directory.

Markdown files with YAML frontmatter are always the source of truth. All interfaces (MCP, web, manual editing) read and write the same files.

## Terminology

| Term | Meaning |
|---|---|
| **Spec** | Any markdown file in `.specs/` — the unit of work definition |
| **Story** | A spec describing what needs to happen from the user's perspective (`type: feature`, `bug`, `chore`, `docs`) |
| **Epic** | A spec that groups related stories into a larger initiative (`type: epic`) |
| **Spike** | A spec for research/exploration that produces ADRs or research docs (`type: spike`) |

## Spec File Format

### Naming Convention

`{PREFIX}-{NUMBER}-{slug}.{type}.md`

- **Prefix**: 1–5 uppercase letters grouping specs by area/project (e.g. `CORE`, `EX`, `DIA`)
- **Number**: Starting at 3 digits (`001`), grows as needed (`1000`+)
- **Slug**: Short descriptive title — what and where
- **Type extension**: `.story.md`, `.epic.md`, `.spike.md` — for visual identification when browsing

### Frontmatter (YAML)

Every spec file starts with YAML frontmatter containing structured metadata:

| Field | Type | Description |
|---|---|---|
| `id` | string | `PREFIX-NNN` format, unique identifier |
| `title` | string | Human-readable title (max ~120 chars) |
| `status` | enum | `pending`, `in-progress`, `in-review`, `done`, `cancelled` |
| `type` | enum | `epic`, `feature`, `bug`, `spike`, `chore`, `docs` |
| `tags` | list[string] | Freeform categorization |
| `business_value` | int | Log-scaled importance, range `[-1000, +1000]` |
| `story_points` | int | Fibonacci sequence: `1, 2, 3, 5, 8, 13, 21` |
| `cycle` | string | Cycle assignment |
| `assignee` | string | Human or agent ID |
| `due_date` | date | Target completion date |
| `dependencies` | list[string] | Spec IDs that must complete before this can start |
| `blocked_by` | list[string] | Explicit blocking relationships |
| `related_to` | list[string] | Informational links, no blocking semantics |
| `parent` | string | Spec ID of the parent epic/story (e.g. `DIA-011`) |
| `created` | date | Creation date |
| `updated` | date | Last modification date |

### Epics as Spec Files

Epics are regular spec files with `type: epic` and `.epic.md` extension. They get their own `PREFIX-NNN` ID, frontmatter, and full markdown body — including vision, behavior scenarios, and acceptance criteria. Child specs reference them via the `parent` field.

This means:
- Epics are numbered and trackable like any other spec
- They participate in the dependency graph
- They have their own acceptance criteria (e.g. "all child stories done")
- The `parent` field can chain: epic → story → subtask

### Body (Markdown)

Customizable via templates per spec type. The body follows a spec-driven + BDD hybrid approach.

**Story template** (`.story.md`):
- **Description** — one-line summary of what the user/agent experiences
- **Context** — the why, with links to ADRs and research docs
- **Behavior** — Given/When/Then scenarios (the contract; tests derive from these)
- **Constraints** — non-functional requirements, boundaries
- **Verification** — how to confirm it's done (maps to test suites)
- **References** — links to ADRs, research docs, related specs
- **Implementation Notes** — filled during work

**Epic template** (`.epic.md`):
- **Vision** — end state from the user's perspective
- **Context** — strategic goal, links to roadmap and ADRs
- **Stories** — child spec list
- **Behavior** — high-level end-to-end scenarios
- **Verification** — epic-level acceptance criteria

**Spike template** (`.spike.md`):
- **Description** — research question
- **Context** — what decision this unblocks
- **Research Questions** — specific questions with clear "answered" states
- **Findings** — answers with evidence
- **Deliverables** — ADR, research doc, and/or architecture update
- **Recommendation** — actionable conclusion

### Workflow

```
write spec → derive tests from behavior scenarios → implement until tests pass → verify against spec
```

Spikes feed into the knowledge base:
```
spike → research doc (docs/research/YYMMDD_slug.md) and/or ADR (docs/adr/NNN-slug.md)
      → informed stories reference these as context
```

## Directory Structure

```
.specs/
├── .gitignore              # Always ignores .cache/
├── .cache/                 # SQLite read cache (always gitignored)
│   └── tasks.db
├── config/
│   ├── settings.yaml       # Tool behavior (statuses, types, ports, etc.)
│   ├── prefixes.yaml       # Prefix definitions + descriptions + template mapping
│   ├── schema.yaml         # Frontmatter validation rules
│   ├── priority.yaml       # WSJF scoring weights
│   ├── cycles.yaml         # Cycle boundary definitions
│   ├── hooks.yaml          # Lifecycle hooks
│   └── templates/
│       ├── story.md        # Story body template (default)
│       ├── epic.md         # Epic body template
│       └── spike.md        # Spike/research template
├── ROADMAP.md              # Explicit phased roadmap with narrative
├── changelog.md            # Append-only structured mutation log
├── backlog/                # Specs not yet scheduled
├── archive/                # Completed or cancelled specs
├── PREFIX-001-slug.story.md
├── PREFIX-002-slug.epic.md
└── ...
```

### Gitignore Strategy

The `.specs/.gitignore` always ignores `.cache/`. Whether spec files themselves are tracked is the user's choice — they manage their project's `.gitignore` as needed. The tool never manages gitignore contents beyond shipping the cache exclusion.

## Documentation Structure

```
docs/
├── spec.md                 # This file — product specification
├── architecture.md         # System architecture, diagrams, data flows
├── adr/                    # Architecture Decision Records
│   ├── template.md
│   ├── 001-slug.md
│   └── ...
└── research/               # Date-prefixed research documents
    ├── YYMMDD_slug.md
    └── ...
```

**ADRs** record major architectural choices (Status, Context, Decision, Consequences). Created by spikes or when making significant technical decisions. They are a primary source for future alignment — always check relevant ADRs before revisiting a settled decision.

**Research docs** capture detailed findings from spikes. Date-prefixed for chronological context. They inform ADRs and provide evidence for decisions.

Both ADRs and research docs are referenced from spec files (Context and References sections) to maintain traceability.

## Cache

**Location**: `.specs/.cache/tasks.db` (SQLite, always gitignored)

**Purpose**: Accelerate listing, filtering, sorting, and full-text search without re-parsing every spec file on every request.

**Contents**:
- Parsed frontmatter (all metadata fields, typed)
- Computed fields: priority score, blocked/unblocked status, dependency graph edges
- FTS5 full-text search index over spec bodies
- Cycle aggregates (velocity, burndown data points)

**Invalidation**:
- File mtime-based — on access, compare cached mtime vs filesystem mtime per spec file
- Lazy revalidation: check on read, not with a background watcher
- Full rebuild on startup (cheap — just parse all spec files)
- Cache version constant — bump to force rebuild when schema changes

**Properties**:
- Deletion is safe — everything rebuilds from spec files
- WAL mode for concurrent read access (MCP + dashboard simultaneously)
- No daemon required

## MCP Server

Exposes spec operations as MCP tools for AI agents via FastMCP 3.x ([ADR-001](adr/001-use-fastmcp-over-official-sdk.md)). Supports stdio (CLI integration) and SSE (networked) transports.

### Tools

| Tool | Description |
|---|---|
| `create_story(prefix, title, **meta)` | Create a new spec file from template, auto-incrementing ID |
| `get_story(spec_id)` | Read a single spec with all metadata and body |
| `update_story(spec_id, **changes)` | Modify spec metadata or body sections |
| `list_stories(filters, sort_by)` | List/filter/sort specs |
| `get_next_story(filters)` | Highest priority unblocked story (respects dependency DAG) |
| `search_stories(query)` | Full-text search across metadata and body |
| `claim_story(spec_id, agent_id)` | Lock a spec for an agent (prevents concurrent work) |
| `release_story(spec_id, agent_id)` | Release a claimed spec |
| `get_dependency_graph(spec_id)` | Show blockers and dependents |
| `validate_specs()` | Check all specs against configured schema |

### Agent UX Principles

- All tools use typed Pydantic models for input/output — agents discover schemas automatically
- `get_next_story()` is the primary entry point: give me work to do, sorted by what matters most
- `create_story()` requires minimal input (prefix + title) — template fills defaults, agent fills details after
- Claim/release with timeout prevents permanently locked specs if an agent crashes
- Changelog tracks agent ID for every mutation

## Web Dashboard

Litestar JSON API backend ([ADR-002](adr/002-litestar-over-fastapi.md)) + React/Vite frontend ([ADR-003](adr/003-react-vite-frontend.md)).

### Views

| View | Description |
|---|---|
| **Kanban board** | Columns per status, drag-and-drop to change status |
| **Spec list** | Sortable, filterable table with inline field editing |
| **Spec detail** | Full spec view with editable frontmatter and markdown body |
| **Dependency graph** | Interactive DAG visualization (React Flow) |
| **Cycle planning** | Drag specs into cycles, see capacity vs committed points |
| **Timeline/Gantt** | Rough scheduling based on story points + velocity |

### Capabilities

- Filter by status, assignee, tags, parent, cycle, due date, prefix
- Sort by priority score, business value, due date, created date
- Live search with results updating as you type
- External file changes reflected on page refresh
- Responsive layout

## Dependency Resolution

Powered by networkx as a DAG (directed acyclic graph).

### Features

- Build graph from `dependencies` and `blocked_by` fields
- Cycle detection with clear error reporting
- Topological sort for valid execution ordering
- Blocked/unblocked status: a spec is blocked if any dependency is not `done`
- `get_unblocked()` — only specs whose entire chain is resolved
- Critical path analysis
- Graph export as JSON for dashboard visualization
- Completing a spec cascades unblocking to dependents

### Relationship Types

| Field | Semantics |
|---|---|
| `dependencies` / `blocked_by` | Hard blocking — can't start until resolved |
| `related_to` | Informational link, no blocking |
| `parent` | Hierarchical decomposition (epic → stories → subtasks) |

## Priority Scoring

Composite WSJF-style priority computed from multiple signals:

```
priority = (business_value × w_bv + time_criticality × w_tc + risk_reduction × w_rr)
           / max(story_points, 1)
           + unblocks_bonus × count_of_specs_this_unblocks
           + age_bonus × days_since_created
           + due_date_urgency
```

- **business_value**: direct from frontmatter
- **time_criticality**: derived from due_date proximity
- **risk_reduction**: optional manual field
- **unblocks_bonus**: rewards specs that unblock many others
- **age_bonus**: prevents starvation (old pending specs drift upward)
- **due_date_urgency**: step function with critical (≤3 days) and warning (≤7 days) thresholds

All weights configurable in `.specs/config/priority.yaml`. `get_next_story()` uses this computed score, not business_value alone.

## Changelog

Append-only structured log at `.specs/changelog.md`.

### Format

```markdown
## 2026-03-27
- CORE-026: status pending → in-progress (agent: claude-abc)
- DIA-020: created (agent: human)
- CORE-027: business_value 100 → 300 (agent: human)
```

One line per change, grouped by date. Git-friendly, grep-friendly. The dashboard can parse it into a timeline view.

All mutations through any interface (MCP, web, or store API) append to the changelog with agent/user attribution.

## Agent Coordination

### Claim/Release

- `claim_story(spec_id, agent_id)` — sets assignee and locks the spec
- `release_story(spec_id, agent_id)` — releases the lock
- Configurable timeout (`claim_timeout_minutes` in settings.yaml) — auto-release if agent doesn't heartbeat
- Dashboard shows "currently being worked on by: agent-xyz"
- Prevents two agents working the same spec concurrently

### Audit Trail

Every change records which agent (human or AI agent ID) made it, via the changelog.

## Schema Validation

Configurable in `.specs/config/schema.yaml`:

- **Required fields** on every spec (id, title, status, type, created)
- **Per-status requirements** (e.g. `in-progress` requires `assignee`)
- **Field type constraints** (enums, ranges, patterns, max lengths)
- **ID format enforcement** (`^[A-Z]{1,5}-\d{3,}$`)

Validation runs:
- On spec creation (MCP and web)
- On spec update (MCP and web)
- On demand via `validate_specs()` MCP tool and CLI command

## Lifecycle Hooks

Configurable in `.specs/config/hooks.yaml`:

- **on_status_change** — e.g. auto-archive on `done`
- **on_create** — e.g. validate frontmatter
- **on_claim_timeout** — e.g. release and notify

## Non-Functional Requirements

- **UX**: Intuitive for both humans (dashboard) and agents (MCP with self-documenting schemas)
- **Anti-hallucination**: Clear, structured definitions with BDD scenarios reduce ambiguity
- **Flexibility**: Accommodate different workflows (agile, kanban) via configurable statuses, templates, and metadata
- **Scalability**: Handle large spec counts without degradation (SQLite cache, lazy invalidation)
- **No database**: Filesystem is the source of truth. SQLite is a disposable read cache.
- **Concurrent access**: File-level locking for writes, WAL mode SQLite for reads
- **Continuity**: ADRs and research docs ensure decisions are traceable and revisitable
