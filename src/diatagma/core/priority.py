"""Composite priority scoring for story ordering.

Computes a single priority score from multiple signals using
configurable WSJF-style weighting:

    priority = (business_value × w_bv) / max(story_points, 1)
             + unblocks_bonus × dependents_count
             + age_bonus_per_day × days_since_created
             + due_date_urgency_bonus

Additional WSJF factors (time_criticality, risk_reduction) have
weights in PriorityWeights but no per-spec fields on SpecMeta yet.
They'll participate once those fields are added.

Key functions:
    compute_priority(spec, graph, config) → float
    rank_specs(specs, graph, config)      → list[Spec]  (sorted)
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from diatagma.core.models import DueDateUrgency, PriorityConfig, Spec


# ---------------------------------------------------------------------------
# Graph protocol (decouples from DIA-005)
# ---------------------------------------------------------------------------


@runtime_checkable
class DependencyLookup(Protocol):
    """Protocol for querying dependency fanout.

    Satisfied by SpecGraph.get_dependents() once DIA-005 is implemented.
    """

    def get_dependents(self, spec_id: str) -> list[str]: ...


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_due_date_urgency(
    due_date: date | None,
    today: date,
    urgency: DueDateUrgency,
) -> float:
    """Compute due-date urgency bonus.

    Returns critical_bonus for overdue or within critical_days,
    warning_bonus for within warning_days, 0 otherwise.
    """
    if due_date is None:
        return 0.0

    days_remaining = (due_date - today).days

    if days_remaining < 0:
        # Overdue
        return urgency.critical_bonus

    if days_remaining <= urgency.critical_days:
        return urgency.critical_bonus

    if days_remaining <= urgency.warning_days:
        return urgency.warning_bonus

    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_priority(
    spec: Spec,
    graph: DependencyLookup | None = None,
    config: PriorityConfig | None = None,
    today: date | None = None,
) -> float:
    """Compute a composite priority score for a single spec.

    Args:
        spec: The spec to score.
        graph: Optional dependency lookup for unblocks bonus.
        config: Priority weights. Defaults to PriorityConfig().
        today: Reference date for age/urgency. Defaults to date.today().

    Returns:
        The computed priority score (higher = more urgent).
    """
    if config is None:
        config = PriorityConfig()
    if today is None:
        today = date.today()

    w = config.weights

    # WSJF base: business_value / effort
    bv = (spec.meta.business_value or 0) * w.business_value
    effort = max(spec.meta.story_points or 1, 1)
    base = bv / effort

    # Unblocks bonus
    dependents_count = len(graph.get_dependents(spec.meta.id)) if graph else 0
    unblocks = w.unblocks_bonus * dependents_count

    # Age bonus (anti-starvation)
    age_days = max((today - spec.meta.created).days, 0)
    age = w.age_bonus_per_day * age_days

    # Due date urgency
    urgency = _compute_due_date_urgency(spec.meta.due_date, today, w.due_date_urgency)

    return base + unblocks + age + urgency


def rank_specs(
    specs: list[Spec],
    graph: DependencyLookup | None = None,
    config: PriorityConfig | None = None,
    today: date | None = None,
) -> list[Spec]:
    """Score and sort specs by priority (descending).

    Mutates ``priority_score`` on each spec, then returns the list
    sorted highest-priority first. Blocked specs are included —
    filtering is the caller's responsibility.
    """
    if config is None:
        config = PriorityConfig()
    if today is None:
        today = date.today()

    for spec in specs:
        spec.priority_score = compute_priority(spec, graph, config, today)

    return sorted(specs, key=lambda s: s.priority_score, reverse=True)


__all__ = [
    "DependencyLookup",
    "compute_priority",
    "rank_specs",
]
