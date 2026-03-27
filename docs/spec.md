# Diatagma — Product Specification

## Overview

File-based task coordination tool with both an MCP server (for AI agents) and a web dashboard (for humans), tracking tasks as plain markdown files in a `.tasks/` directory.

Markdown files with YAML frontmatter are always the source of truth. All interfaces (MCP, web, manual editing) read and write the same files.

## Task File Format

### Naming Convention

`{PREFIX}-{NUMBER}-{slug}.md`

- **Prefix**: 1–5 uppercase letters grouping tasks by type, project, or area (e.g. `CORE`, `EX`, `DIA`)
- **Number**: Starting at 3 digits (`001`), grows as needed (`1000`+)
- **Slug**: Short descriptive title — what and where

### Frontmatter (YAML)

Every task file starts with YAML frontmatter containing structured metadata:

| Field | Type | Description |
|---|---|---|
| `id` | string | `PREFIX-NNN` format, unique identifier |
| `title` | string | Human-readable title (max ~120 chars) |
| `status` | enum | `pending`, `in-progress`, `in-review`, `done`, `cancelled` |
| `type` | enum | `epic`, `feature`, `bug`, `spike`, `chore`, `docs` |
| `tags` | list[string] | Freeform categorization |
| `business_value` | int | Log-scaled importance, range `[-1000, +1000]` |
| `story_points` | int | Fibonacci sequence: `1, 2, 3, 5, 8, 13, 21` |
| `sprint` | string | Sprint assignment |
| `assignee` | string | Human or agent ID |
| `due_date` | date | Target completion date |
| `dependencies` | list[string] | Task IDs that must complete before this can start |
| `blocked_by` | list[string] | Explicit blocking relationships |
| `related_to` | list[string] | Informational links, no blocking semantics |
| `parent` | string | Task ID of the parent epic/story (e.g. `DIA-011`) |
| `created` | date | Creation date |
| `updated` | date | Last modification date |

### Epics as Task Files

Epics are regular task files with `type: epic`. They get their own `PREFIX-NNN` ID, frontmatter, and full markdown body — including vision, requirements, and acceptance criteria. Child tasks reference them via the `parent` field using the epic's task ID.

This means:
- Epics are numbered and trackable like any other task
- They participate in the dependency graph
- They have their own acceptance criteria (e.g. "all child tasks done")
- The `parent` field can chain: epic → story → subtask

### Body (Markdown)

Customizable via templates. Default sections:

- **Description** — one-line summary of what this task accomplishes
- **Context** — the why: what problem it solves, what motivated it
- **Requirements** — the what, preferably in user story format ("As a [role], I want [capability] so that [benefit]")
- **Acceptance Criteria** — precise, verifiable conditions for "done", written so an agent can work toward them without interrupting the user
- **Implementation Details** — optional, filled during work, easy to append to

## Directory Structure

```
.tasks/
├── .gitignore              # Always ignores .cache/; user decides about *.md
├── .cache/                 # SQLite read cache (always gitignored)
│   └── tasks.db
├── config/
│   ├── settings.yaml       # Tool behavior (statuses, types, ports, etc.)
│   ├── prefixes.yaml       # Prefix definitions + descriptions + template mapping
│   ├── schema.yaml         # Frontmatter validation rules (required fields, types, per-status)
│   ├── priority.yaml       # WSJF scoring weights
│   ├── sprints.yaml        # Sprint boundary definitions
│   ├── hooks.yaml          # Lifecycle hooks (on status change, on create, etc.)
│   └── templates/
│       ├── default.md      # Fallback body template
│       ├── spike.md        # Research/exploration template
│       └── {PREFIX}.md     # Per-prefix templates
├── changelog.md            # Append-only structured mutation log
├── backlog/                # Tasks not yet scheduled
├── archive/                # Completed or cancelled tasks
├── PREFIX-001-slug.md      # Active tasks
└── ...
```

### Gitignore Strategy

The `.tasks/.gitignore` always ignores `.cache/`. Whether task files themselves are tracked is the user's choice — they add patterns to `.gitignore` as needed. The tool never manages gitignore contents beyond shipping the cache exclusion.

## Cache

**Location**: `.tasks/.cache/tasks.db` (SQLite, always gitignored)

**Purpose**: Accelerate listing, filtering, sorting, and full-text search without re-parsing every markdown file on every request.

**Contents**:
- Parsed frontmatter (all metadata fields, typed)
- Computed fields: priority score, blocked/unblocked status, dependency graph edges
- FTS5 full-text search index over task bodies
- Sprint aggregates (velocity, burndown data points)

**Invalidation**:
- File mtime-based — on access, compare cached mtime vs filesystem mtime per task file
- Lazy revalidation: check on read, not with a background watcher
- Full rebuild on startup (cheap — just parse all .md files)
- Cache version constant — bump to force rebuild when schema changes

**Properties**:
- Deletion is safe — everything rebuilds from markdown files
- WAL mode for concurrent read access (MCP + dashboard simultaneously)
- No daemon required

## MCP Server

Exposes task operations as MCP tools for AI agents via FastMCP 3.x. Supports stdio (CLI integration) and SSE (networked) transports.

### Tools

| Tool | Description |
|---|---|
| `create_task(prefix, title, **meta)` | Create a new task file from template, auto-incrementing ID |
| `get_task(task_id)` | Read a single task with all metadata and body |
| `update_task(task_id, **changes)` | Modify task metadata or body sections |
| `list_tasks(filters, sort_by)` | List/filter/sort tasks |
| `get_next_task(filters)` | Highest priority unblocked task (respects dependency DAG) |
| `search_tasks(query)` | Full-text search across metadata and body |
| `claim_task(task_id, agent_id)` | Lock a task for an agent (prevents concurrent work) |
| `release_task(task_id, agent_id)` | Release a claimed task |
| `get_dependency_graph(task_id)` | Show blockers and dependents |
| `validate_tasks()` | Check all tasks against configured schema |

### Agent UX Principles

- All tools use typed Pydantic models for input/output — agents discover schemas automatically
- `get_next_task()` is the primary entry point: give me work to do, sorted by what matters most
- `create_task()` requires minimal input (prefix + title) — template fills defaults, agent fills details after
- Claim/release with timeout prevents permanently locked tasks if an agent crashes
- Changelog tracks agent ID for every mutation

## Web Dashboard

FastAPI + HTMX + Jinja2. No SPA, no JS build step. HTMX handles interactivity; minimal vanilla JS only where HTMX can't reach (e.g. graph visualization).

### Views

| View | Description |
|---|---|
| **Kanban board** | Columns per status, drag-and-drop to change status |
| **Task list** | Sortable, filterable table with inline field editing |
| **Task detail** | Full task view with editable frontmatter and markdown body |
| **Dependency graph** | Interactive DAG visualization (d3-force or vis.js) |
| **Sprint planning** | Drag tasks into sprints, see capacity vs committed points |
| **Timeline/Gantt** | Rough scheduling based on story points + velocity |

### Capabilities

- Filter by status, assignee, tags, epic, sprint, due date, prefix
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
- Blocked/unblocked status: a task is blocked if any dependency is not `done`
- `get_unblocked_tasks()` — only tasks whose entire chain is resolved
- Critical path analysis
- Graph export as JSON for dashboard visualization
- Completing a task cascades unblocking to dependents

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
           + unblocks_bonus × count_of_tasks_this_unblocks
           + age_bonus × days_since_created
           + due_date_urgency
```

- **business_value**: direct from frontmatter
- **time_criticality**: derived from due_date proximity
- **risk_reduction**: optional manual field
- **unblocks_bonus**: rewards tasks that unblock many others
- **age_bonus**: prevents task starvation (old pending tasks drift upward)
- **due_date_urgency**: step function with critical (≤3 days) and warning (≤7 days) thresholds

All weights configurable in `.tasks/config/priority.yaml`. `get_next_task()` uses this computed score, not business_value alone.

## Changelog

Append-only structured log at `.tasks/changelog.md`.

### Format

```markdown
## 2026-03-27
- CORE-026: status pending → in-progress (agent: claude-abc)
- S1-020: created (agent: human)
- CORE-027: business_value 100 → 300 (agent: human)
```

One line per change, grouped by date. Git-friendly, grep-friendly. The dashboard can parse it into a timeline view.

All mutations through any interface (MCP, web, or store API) append to the changelog with agent/user attribution.

## Agent Coordination

### Claim/Release

- `claim_task(task_id, agent_id)` — sets assignee and locks the task
- `release_task(task_id, agent_id)` — releases the lock
- Configurable timeout (`claim_timeout_minutes` in settings.yaml) — auto-release if agent doesn't heartbeat
- Dashboard shows "currently being worked on by: agent-xyz"
- Prevents two agents working the same task concurrently

### Audit Trail

Every change records which agent (human or AI agent ID) made it, via the changelog.

## Schema Validation

Configurable in `.tasks/config/schema.yaml`:

- **Required fields** on every task (id, title, status, type, created)
- **Per-status requirements** (e.g. `in-progress` requires `assignee`)
- **Field type constraints** (enums, ranges, patterns, max lengths)
- **ID format enforcement** (`^[A-Z]{1,5}-\d{3,}$`)

Validation runs:
- On task creation (MCP and web)
- On task update (MCP and web)
- On demand via `validate_tasks()` MCP tool and CLI command

## Lifecycle Hooks

Configurable in `.tasks/config/hooks.yaml`:

- **on_status_change** — e.g. auto-archive on `done`
- **on_create** — e.g. validate frontmatter
- **on_claim_timeout** — e.g. release and notify

## Non-Functional Requirements

- **UX**: Intuitive for both humans (dashboard) and agents (MCP with self-documenting schemas)
- **Anti-hallucination**: Clear, structured definitions reduce boilerplate and ambiguity in task descriptions
- **Flexibility**: Accommodate different workflows (agile, kanban) via configurable statuses, templates, and metadata
- **Scalability**: Handle large task counts without degradation (SQLite cache, lazy invalidation)
- **No database**: Filesystem is the source of truth. SQLite is a disposable read cache.
- **Concurrent access**: File-level locking for writes, WAL mode SQLite for reads
