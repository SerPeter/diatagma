"""Composite priority scoring for story ordering.

Computes a single priority score from multiple signals using
configurable WSJF-style weighting:

    priority = (business_value + time_criticality + risk_reduction) / story_points

Additional factors: blocked_count (how many specs this unblocks),
spec age, due date proximity. Weights loaded from
.tasks/config/priority.yaml.

Key functions:
    compute_priority(spec, graph, config) → float
    rank_specs(specs, graph, config)      → list[Spec]  (sorted)
"""
