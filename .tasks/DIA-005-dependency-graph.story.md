---
id: DIA-005
title: "Build networkx dependency DAG with blocking semantics"
status: done
type: feature
tags: [core, graph, dependencies]
business_value: 400
story_points: 5
parent: DIA-011
dependencies: [DIA-001]
assignee: ""
created: 2026-03-27
---

## Description

Implement the TaskGraph class using networkx to manage task dependencies, detect cycles, compute blocked/unblocked status, and provide topological ordering.

## Context

Dependencies are central to get_next_task() — agents need to know which tasks are actually ready to work on. The graph also powers the dashboard's dependency visualization.

## Requirements

- [ ] Build DAG from task dependencies and blocked_by fields
- [ ] `is_blocked(task_id)` — true if any dependency is not done
- [ ] `get_unblocked()` — all tasks whose dependencies are satisfied
- [ ] `get_blockers(task_id)` — transitive blockers
- [ ] `get_dependents(task_id)` — what this task unblocks
- [ ] `detect_cycles()` — return cycle paths for validation
- [ ] `topological_sort()` — valid execution order
- [ ] Export graph as JSON for dashboard visualization

## Acceptance Criteria

- [ ] Cycle detection catches circular dependencies and reports them clearly
- [ ] Completing a task updates blocked status of dependents
- [ ] Graph export produces valid d3-force compatible JSON
- [ ] Handles orphan tasks (no dependencies) correctly

## Implementation Details
