---
id: DIA-022
title: "Design web dashboard UX: wireframes and interaction spec for all views"
status: pending
type: story
tags: [web, ux, design, refine]
business_value: 400
story_points: 5
parent: DIA-013
assignee: ""
created: 2026-03-29
links:
  relates_to: [DIA-010]
---

## Description

Produce a complete UX design (wireframes + interaction spec) for the diatagma web dashboard — a browser-based interface for managing markdown-based project specs.

## Context

Diatagma is a spec-driven project coordination tool. Specs are markdown files with YAML frontmatter stored in a `.specs/` directory. Each spec has metadata (ID, title, status, type, priority score, tags, assignee, dependencies, parent) and a markdown body. The dashboard is the human interface for viewing, creating, editing, and coordinating these specs. It will be built with React + Vite (SPA) consuming a JSON API.

The dashboard must serve two user profiles:
1. **Project leads** who triage, prioritize, and plan work across specs
2. **Individual developers** who need to quickly find their next task, see what's blocked, and update status

The design should be informed by these UX principles observed in the best developer tools:
- **Speed over features**: sub-second interactions, no loading spinners for common operations
- **Keyboard-first**: every primary workflow completable without mouse. Power users never leave the keyboard.
- **Information density**: developers prefer dense, scannable views over spacious layouts. Show more data, fewer decorations.
- **Opinionated defaults with escape hatches**: start simple, allow depth. Don't overwhelm on first load.
- **Context preservation**: navigating to a detail view and back should not lose list state (filters, scroll position, sort)

### Data Model Reference

Each spec has this metadata (YAML frontmatter):

```yaml
id: "DIA-015"              # Unique identifier (PREFIX-NNN)
title: "Get ready specs"   # Short title (max 120 chars)
status: pending            # pending | blocked | in-progress | in-review | done | cancelled
type: story                # story | epic | spike | bug
tags: [core, query]        # Freeform string tags
business_value: 500        # -1000 to 1000
story_points: 5            # 1, 2, 3, 5, 8, 13, 21
parent: "DIA-011"          # Parent epic ID (optional)
links:
  blocked_by: ["DIA-005"]    # Specs that must complete before this one
  relates_to: ["DIA-009"]    # Related specs (no blocking)
  supersedes: []             # Specs this one replaces
assignee: "agent-a"        # Who is working on this
cycle: "Cycle 1"         # Cycle assignment (optional)
due_date: 2026-04-15       # Deadline (optional)
created: 2026-03-29
```

And a markdown body with sections like Description, Context, Behavior (Given/When/Then scenarios), Constraints, Verification, References, Implementation Notes.

### Status Workflow

```
pending → blocked (manual or auto when dependency added)
pending → in-progress (when work starts / agent claims)
in-progress → in-review
in-review → done
any → cancelled
blocked → pending (auto when blockers resolve)
```

### Spec Types

- **Story**: unit of deliverable work (most common)
- **Epic**: groups related stories under a parent; auto-completes when all children are done
- **Spike**: research task producing ADRs or research documents
- **Bug**: defect report with reproduction steps and root cause analysis

### Priority System

Specs have a computed priority score (higher = more important) based on: business value, story points, how many other specs they unblock, age, and due date urgency. The "ready" query returns only unblocked pending specs, sorted by this score.

### Tags

Freeform. Notable convention: `refine` tag means the spec needs more detail before work can start.

---

## Views to Design

### 1. Kanban Board (Primary View)

The default view. Columns represent statuses.

**Requirements:**
- Columns: pending, blocked, in-progress, in-review, done (cancelled hidden by default, toggleable)
- Cards show: ID, title, type icon, assignee avatar/initials, story points badge, priority indicator, tags
- Cards within each column sorted by priority score (highest at top)
- Drag-and-drop cards between columns to change status
- Visual distinction for spec types (story, epic, spike, bug) — icon or color accent, not overwhelming
- Epic cards should show child progress (e.g., "5/8 done" mini progress bar)
- Blocked cards should show what's blocking them (tooltip or inline chip with blocker ID)
- Column header shows count of specs in that column
- Filter bar above board: filter by type, tags, assignee, cycle, parent epic
- Active filters should be visible as removable chips

### 2. List View

Dense, tabular, sortable — for power users who want to see everything at once.

**Requirements:**
- Table columns: ID, title, status, type, assignee, story points, priority score, tags, parent, cycle, created, due date
- All columns sortable (click header to sort/reverse)
- All columns filterable (same filter bar as kanban)
- Inline status change (click status cell → dropdown)
- Row click opens detail view
- Bulk selection (checkboxes) for batch status changes
- Compact row height — maximize visible specs
- Alternate row shading for readability

### 3. Spec Detail View

Full view of a single spec — metadata + markdown body.

**Requirements:**
- Appears as a slide-over panel (right side) or modal, not a full page navigation (preserves list/board context)
- Header: ID, title (editable inline), status badge (clickable to change), type icon
- Metadata grid: assignee, story points, business value, tags, cycle, due date, parent, blocked_by, relates_to — all editable inline
- Dependency section: visual list of blockers (with their status) and specs this one unblocks
- Markdown body rendered with section headers
- Edit mode: toggle to edit frontmatter fields and body markdown (side-by-side preview or tabbed)
- Timeline/activity: changelog entries for this spec (status changes, field updates, who/when)

### 4. Dependency Graph View

Interactive visualization of the spec dependency DAG.

**Requirements:**
- Force-directed or hierarchical graph layout
- Nodes represent specs: show ID + title, colored by status
- Edges represent relationships: solid arrows for `blocked_by`, dashed for `relates_to`, dotted for `supersedes`
- Click a node to open its detail view
- Highlight path: click a node to highlight all upstream blockers and downstream dependents
- Filter: show only a subtree (e.g., "show me everything connected to DIA-011")
- Zoom and pan controls
- Minimap for large graphs

### 5. Epic/Parent View

Focused view of an epic and its children.

**Requirements:**
- Epic header: title, status, overall progress bar (X/Y children done)
- Children listed as mini-cards or compact rows, grouped by status
- Same drag-and-drop status changes as kanban but scoped to this epic's children
- Burndown or progress indicator (if cycle is set)

### 6. Cycle View (if cycle is configured)

**Requirements:**
- Cycle header: name, date range, goal, progress bar
- Specs in the cycle shown as kanban or list (user's choice)
- Velocity/capacity indicators if historical data exists
- "Unfinished" section showing specs that didn't complete in time

---

## Global UI Elements

### Navigation
- Left sidebar or top nav with view switcher: Kanban | List | Graph | Cycle
- Current view highlighted
- Breadcrumbs when drilling into epic or detail views

### Command Palette / Search
- Triggered by `/` key (or `Cmd+K` / `Ctrl+K`)
- Search across: spec ID, title, body content, tags
- Recent specs section
- Quick actions: "Create story", "Go to DIA-015", "Filter by tag:core"

### Keyboard Shortcuts
- `/` or `Cmd+K`: Open command palette / search
- `n`: Create new spec
- `j` / `k`: Navigate down/up in list or between cards
- `Enter`: Open detail view for focused spec
- `Esc`: Close detail/modal, clear search
- `1-5`: Switch views (1=Kanban, 2=List, 3=Graph, 4=Cycle)
- `s`: Focus status dropdown for selected spec
- `?`: Show keyboard shortcut reference

### Notifications / Toasts
- Success: "DIA-015 → in-progress" (brief, auto-dismiss)
- Info: "DIA-011 auto-completed (all children done)"
- Warning: "DIA-021 has circular dependency"
- Position: bottom-right, stackable, dismissible

### Empty States
- No specs yet: guidance to create first spec or run `diatagma init`
- No results for filter: "No specs match filters. [Clear filters]"
- No specs in cycle: "No specs assigned to this cycle yet"

### Color & Visual Language
- Status colors: pending (gray), blocked (red/orange), in-progress (blue), in-review (purple), done (green), cancelled (muted/strikethrough)
- Type indicators: story (default), epic (distinct icon — layers/stack), spike (lightbulb/research), bug (bug icon)
- Priority: subtle gradient or bar intensity (not a separate color — avoid rainbow overload)
- Dark mode support (respect system preference, toggleable)
- Minimal chrome: content over decoration

---

## Responsive Behavior

- **Desktop (>1200px)**: Full layout — sidebar nav + main content + detail panel
- **Tablet (768-1200px)**: Collapsed sidebar (icons only), detail view as overlay
- **Mobile (<768px)**: Out of scope for initial design. Dashboard is a desktop/tablet tool.

---

## Deliverables

- [ ] Wireframes for all 6 views (Kanban, List, Detail, Graph, Epic, Cycle)
- [ ] Wireframes for global elements (nav, command palette, keyboard shortcut reference, empty states)
- [ ] Interaction spec: what happens on each user action (click, drag, keyboard shortcut)
- [ ] Responsive breakpoint sketches (desktop + tablet)
- [ ] Component inventory: list of reusable UI components identified across views
- [ ] Color/status mapping reference

## Constraints

- Design for React + Vite implementation (component-based, SPA)
- All views share the same filter state (switching Kanban → List preserves active filters)
- No full-page navigations — use panels, overlays, and view switching
- Wireframes are sufficient — no need for high-fidelity mockups or pixel-perfect designs at this stage
- Assume data comes from a JSON API (REST endpoints for specs, graph, search)

## Verification

- [ ] Every view has a wireframe covering its primary and empty state
- [ ] All keyboard shortcuts documented in interaction spec
- [ ] Drag-and-drop behavior specified for kanban
- [ ] Detail view interaction (open/close, edit mode) fully specified
- [ ] Filter behavior documented (what filters exist, how they persist, how they're cleared)
- [ ] Status color mapping and type iconography defined

## References

## Implementation Notes
