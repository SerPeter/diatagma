"""Get-next query — "what should I work on next?"

Composes dependency resolution (graph), priority ranking, and status/claim
filtering into a single deterministic query. This is the highest-value
entry point for both agents and humans.

Key function:
    get_next(store, graph, *, n, include_claimed, tags, type, cycle, ...)
        → list[Spec]
"""

from __future__ import annotations

import re
from datetime import date

from loguru import logger

from diatagma.core.graph import SpecGraph
from diatagma.core.models import PriorityConfig, Spec
from diatagma.core.priority import rank_specs

# ---------------------------------------------------------------------------
# ID sort key (deterministic tiebreaker)
# ---------------------------------------------------------------------------

_ID_NUM_RE = re.compile(r"^([A-Z]{1,5})-(\d{3,})")


def _id_sort_key(spec: Spec) -> tuple[str, int]:
    """Sort key: prefix alphabetically, then number ascending."""
    m = _ID_NUM_RE.match(spec.meta.id)
    if m:
        return (m.group(1), int(m.group(2)))
    return (spec.meta.id, 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_next(
    specs: list[Spec],
    graph: SpecGraph,
    *,
    n: int | None = None,
    include_claimed: bool = False,
    tags: list[str] | None = None,
    type: str | None = None,
    cycle: str | None = None,
    config: PriorityConfig | None = None,
    today: date | None = None,
) -> list[Spec]:
    """Return the next specs to work on, sorted by priority.

    Combines dependency resolution, priority ranking, and filtering
    into a single deterministic query.

    Args:
        specs: All specs (the graph must already be built from these).
        graph: A built SpecGraph for dependency/cycle queries.
        n: Maximum number of specs to return. None = all.
        include_claimed: If False (default), exclude specs with a
            non-empty assignee.
        tags: Only include specs matching at least one of these tags.
        type: Only include specs of this type.
        cycle: Only include specs in this cycle.
        config: Priority scoring configuration.
        today: Reference date for priority scoring.

    Returns:
        Specs sorted by priority descending, then by ID ascending
        as a deterministic tiebreaker. Never includes epics or specs
        involved in circular dependencies.
    """
    # 1. Detect and exclude circular dependency participants
    dep_cycles = graph.detect_cycles()
    cycle_ids: set[str] = set()
    if dep_cycles:
        for dep_cycle in dep_cycles:
            cycle_ids.update(dep_cycle)
        logger.warning(
            "circular dependencies detected, excluding {} specs: {}",
            len(cycle_ids),
            sorted(cycle_ids),
        )

    # 2. Get unblocked spec IDs (already excludes done/cancelled)
    unblocked_ids = set(graph.get_unblocked()) - cycle_ids

    # 3. Build spec lookup and filter
    candidates: list[Spec] = []
    for spec in specs:
        sid = spec.meta.id

        # Must be unblocked
        if sid not in unblocked_ids:
            continue

        # Never return epics
        if spec.meta.type == "epic":
            continue

        # Exclude claimed specs unless requested
        if not include_claimed and spec.meta.assignee:
            continue

        # Optional filters
        if type is not None and spec.meta.type != type:
            continue

        if tags is not None and not (set(tags) & set(spec.meta.tags)):
            continue

        if cycle is not None and spec.meta.cycle != cycle:
            continue

        candidates.append(spec)

    # 4. Score and sort by priority (descending)
    ranked = rank_specs(candidates, graph, config, today)

    # 5. Deterministic tiebreaker: equal priority → ID ascending
    ranked.sort(key=lambda s: (-s.priority_score, _id_sort_key(s)))

    # 6. Limit
    if n is not None:
        ranked = ranked[:n]

    return ranked


__all__ = [
    "get_next",
]
