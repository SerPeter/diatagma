"""Composite priority scoring for task ordering.

Computes a single priority score from multiple signals using
configurable WSJF-style weighting:

    priority = (business_value + time_criticality + risk_reduction) / story_points

Additional factors: blocked_count (how many tasks this unblocks),
task age, due date proximity. Weights loaded from
.tasks/config/priority.yaml.

Key functions:
    compute_priority(task, graph, config) → float
    rank_tasks(tasks, graph, config)      → list[Task]  (sorted)
"""
