"""Tests for core.next — get_next query."""

from __future__ import annotations

from datetime import date
from typing import Literal

from diatagma.core.graph import SpecGraph
from diatagma.core.models import Spec, SpecBody, SpecLinks, SpecMeta
from diatagma.core.next import get_next

type StoryPoints = Literal[1, 2, 3, 5, 8, 13, 21] | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(
    spec_id: str,
    *,
    status: str = "pending",
    spec_type: str = "feature",
    blocked_by: list[str] | None = None,
    assignee: str | None = None,
    tags: list[str] | None = None,
    cycle: str | None = None,
    business_value: int | None = None,
    story_points: StoryPoints = None,
) -> Spec:
    """Build a minimal Spec for testing."""
    links = SpecLinks(blocked_by=blocked_by or [])
    meta = SpecMeta(
        id=spec_id,
        title=f"Spec {spec_id}",
        type=spec_type,
        status=status,
        links=links,
        assignee=assignee,
        tags=tags or [],
        cycle=cycle,
        business_value=business_value,
        story_points=story_points,
        created=date(2026, 3, 27),
    )
    return Spec(meta=meta, body=SpecBody())


def _build(specs: list[Spec]) -> SpecGraph:
    """Build a SpecGraph from specs."""
    g = SpecGraph()
    g.build(specs)
    return g


# Fixed date for deterministic scoring
TODAY = date(2026, 3, 30)


# ===========================================================================
# TestBasic
# ===========================================================================


class TestBasic:
    """Core get_next behavior."""

    def test_returns_unblocked_pending_specs(self):
        specs = [
            _spec("DIA-001", status="done"),
            _spec("DIA-002", status="pending"),
            _spec("DIA-003", status="pending", blocked_by=["DIA-002"]),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-002"]

    def test_sorted_by_priority_descending(self):
        specs = [
            _spec("DIA-001", business_value=100),
            _spec("DIA-002", business_value=500),
            _spec("DIA-003", business_value=300),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        ids = [s.meta.id for s in result]
        assert ids[0] == "DIA-002"  # highest bv
        assert ids[1] == "DIA-003"
        assert ids[2] == "DIA-001"


# ===========================================================================
# TestCount
# ===========================================================================


class TestCount:
    """Limit parameter."""

    def test_n_limits_results(self):
        specs = [_spec(f"DIA-{i:03d}") for i in range(1, 11)]
        graph = _build(specs)
        result = get_next(specs, graph, n=3, today=TODAY)
        assert len(result) == 3

    def test_n_none_returns_all(self):
        specs = [_spec(f"DIA-{i:03d}") for i in range(1, 6)]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert len(result) == 5

    def test_n_larger_than_available(self):
        specs = [_spec("DIA-001"), _spec("DIA-002")]
        graph = _build(specs)
        result = get_next(specs, graph, n=10, today=TODAY)
        assert len(result) == 2


# ===========================================================================
# TestExcludeEpics
# ===========================================================================


class TestExcludeEpics:
    """Epics are never returned."""

    def test_epics_excluded(self):
        specs = [
            _spec("DIA-001", spec_type="epic"),
            _spec("DIA-002", spec_type="feature"),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-002"]

    def test_only_epics_returns_empty(self):
        specs = [_spec("DIA-001", spec_type="epic")]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert result == []


# ===========================================================================
# TestExcludeClaimed
# ===========================================================================


class TestExcludeClaimed:
    """Claimed (assigned) specs excluded by default."""

    def test_claimed_excluded_by_default(self):
        specs = [
            _spec("DIA-001", assignee="alice"),
            _spec("DIA-002"),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-002"]

    def test_claimed_included_when_requested(self):
        specs = [
            _spec("DIA-001", assignee="alice"),
            _spec("DIA-002"),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, include_claimed=True, today=TODAY)
        assert len(result) == 2

    def test_empty_assignee_not_treated_as_claimed(self):
        specs = [_spec("DIA-001", assignee="")]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert len(result) == 1


# ===========================================================================
# TestFilters
# ===========================================================================


class TestFilters:
    """Optional tag, type, cycle filters."""

    def test_filter_by_tags(self):
        specs = [
            _spec("DIA-001", tags=["core", "api"]),
            _spec("DIA-002", tags=["web"]),
            _spec("DIA-003", tags=["core"]),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, tags=["core"], today=TODAY)
        ids = {s.meta.id for s in result}
        assert ids == {"DIA-001", "DIA-003"}

    def test_filter_by_type(self):
        specs = [
            _spec("DIA-001", spec_type="feature"),
            _spec("DIA-002", spec_type="bug"),
            _spec("DIA-003", spec_type="feature"),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, type="bug", today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-002"]

    def test_filter_by_cycle(self):
        specs = [
            _spec("DIA-001", cycle="Cycle 1"),
            _spec("DIA-002", cycle="Cycle 2"),
            _spec("DIA-003"),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, cycle="Cycle 1", today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-001"]

    def test_combined_filters(self):
        specs = [
            _spec("DIA-001", spec_type="feature", tags=["core"], cycle="Cycle 1"),
            _spec("DIA-002", spec_type="bug", tags=["core"], cycle="Cycle 1"),
            _spec("DIA-003", spec_type="feature", tags=["web"], cycle="Cycle 1"),
        ]
        graph = _build(specs)
        result = get_next(
            specs, graph, type="feature", tags=["core"], cycle="Cycle 1", today=TODAY
        )
        assert [s.meta.id for s in result] == ["DIA-001"]


# ===========================================================================
# TestCircularDependencies
# ===========================================================================


class TestCircularDependencies:
    """Specs in cycles are excluded."""

    def test_cycle_participants_excluded(self):
        specs = [
            _spec("DIA-001", blocked_by=["DIA-002"]),
            _spec("DIA-002", blocked_by=["DIA-001"]),
            _spec("DIA-003"),  # not in cycle
        ]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-003"]

    def test_cycle_warning_logged(self):
        from loguru import logger

        specs = [
            _spec("DIA-001", blocked_by=["DIA-002"]),
            _spec("DIA-002", blocked_by=["DIA-001"]),
        ]
        graph = _build(specs)
        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(str(m)), level="WARNING")
        try:
            get_next(specs, graph, today=TODAY)
        finally:
            logger.remove(sink_id)
        assert any("circular dependencies" in m.lower() for m in messages)


# ===========================================================================
# TestDeterministicOrder
# ===========================================================================


class TestDeterministicOrder:
    """Equal-priority specs ordered by ID ascending."""

    def test_tiebreaker_by_id(self):
        # All specs have same business_value and story_points → equal priority
        specs = [
            _spec("DIA-003", business_value=100),
            _spec("DIA-001", business_value=100),
            _spec("DIA-002", business_value=100),
        ]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        ids = [s.meta.id for s in result]
        assert ids == ["DIA-001", "DIA-002", "DIA-003"]

    def test_deterministic_across_calls(self):
        specs = [_spec(f"DIA-{i:03d}") for i in range(1, 6)]
        graph = _build(specs)
        r1 = [s.meta.id for s in get_next(specs, graph, today=TODAY)]
        r2 = [s.meta.id for s in get_next(specs, graph, today=TODAY)]
        assert r1 == r2


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Empty and boundary conditions."""

    def test_empty_specs(self):
        graph = _build([])
        assert get_next([], graph, today=TODAY) == []

    def test_all_blocked(self):
        specs = [
            _spec("DIA-001", blocked_by=["DIA-002"]),
            _spec("DIA-002", blocked_by=["DIA-001"]),
        ]
        graph = _build(specs)
        assert get_next(specs, graph, today=TODAY) == []

    def test_all_done(self):
        specs = [
            _spec("DIA-001", status="done"),
            _spec("DIA-002", status="cancelled"),
        ]
        graph = _build(specs)
        assert get_next(specs, graph, today=TODAY) == []

    def test_all_epics(self):
        specs = [_spec("DIA-001", spec_type="epic")]
        graph = _build(specs)
        assert get_next(specs, graph, today=TODAY) == []

    def test_in_progress_not_returned(self):
        """in-progress specs are not 'done' but also not 'unblocked pending'
        — get_unblocked includes them since they're not done/cancelled.
        They should still appear in get_next (they're active work)."""
        specs = [_spec("DIA-001", status="in-progress")]
        graph = _build(specs)
        result = get_next(specs, graph, today=TODAY)
        assert [s.meta.id for s in result] == ["DIA-001"]
