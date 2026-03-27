---
id: DIA-006
title: "Implement WSJF priority scoring and task ranking"
status: pending
type: feature
tags: [core, priority]
business_value: 300
story_points: 3
parent: DIA-011
dependencies: [DIA-001, DIA-005]
assignee: ""
created: 2026-03-27
---

## Description

Compute composite priority scores using configurable WSJF-style weighting, incorporating business value, story points, dependency fanout, age, and due date urgency.

## Context

Agents calling get_next_task() need a single ranked list. Manual business_value alone isn't enough — a low-value task that unblocks five high-value tasks should rank higher.

## Requirements

- [ ] `compute_priority(task, graph, config) → float`
- [ ] `rank_tasks(tasks, graph, config) → list[Task]` (sorted descending)
- [ ] Weights loaded from .tasks/config/priority.yaml
- [ ] Factors: business_value, story_points, unblocks_count, age, due_date proximity

## Acceptance Criteria

- [ ] A task blocking many others ranks higher than an isolated task of equal value
- [ ] Overdue tasks get urgency boost
- [ ] Old pending tasks don't starve (age bonus)
- [ ] Weights are configurable without code changes

## Implementation Details
