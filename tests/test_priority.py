"""Tests for core.priority — WSJF scoring and spec ranking."""

from datetime import date

import pytest

from diatagma.core.models import (
    DueDateUrgency,
    PriorityConfig,
    PriorityWeights,
    Spec,
    SpecBody,
    SpecMeta,
)
from diatagma.core.priority import (
    DependencyLookup,
    _compute_due_date_urgency,
    compute_priority,
    rank_specs,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TODAY = date(2026, 3, 28)


def _make_spec(
    spec_id: str = "TST-001",
    title: str = "Test spec",
    spec_type: str = "feature",
    business_value: int | None = 100,
    story_points: int | None = 5,
    created: date = date(2026, 3, 1),
    due_date: date | None = None,
    **extra_meta,
) -> Spec:
    """Build a Spec for priority testing."""
    meta = SpecMeta.model_validate(
        {
            "id": spec_id,
            "title": title,
            "type": spec_type,
            "business_value": business_value,
            "story_points": story_points,
            "created": created,
            "due_date": due_date,
            **extra_meta,
        }
    )
    return Spec(meta=meta, body=SpecBody())


class MockGraph:
    """Dict-backed DependencyLookup for testing."""

    def __init__(self, dependents: dict[str, list[str]] | None = None) -> None:
        self._dependents = dependents or {}

    def get_dependents(self, spec_id: str) -> list[str]:
        return self._dependents.get(spec_id, [])


# ---------------------------------------------------------------------------
# TestComputePriority
# ---------------------------------------------------------------------------


class TestComputePriority:
    """Tests for compute_priority()."""

    def test_base_score(self, priority_config: PriorityConfig) -> None:
        """business_value * w_bv / story_points."""
        spec = _make_spec(business_value=100, story_points=5)
        score = compute_priority(spec, config=priority_config, today=TODAY)
        # base = 100 * 1.0 / 5 = 20.0, age = 27 * 0.5 = 13.5, total = 33.5
        assert score == pytest.approx(33.5)

    def test_no_story_points_defaults_to_one(
        self, priority_config: PriorityConfig
    ) -> None:
        """story_points=None should default to 1."""
        spec = _make_spec(business_value=100, story_points=None)
        score = compute_priority(spec, config=priority_config, today=TODAY)
        # base = 100 * 1.0 / 1 = 100.0, age = 27 * 0.5 = 13.5
        assert score == pytest.approx(113.5)

    def test_negative_business_value(self, priority_config: PriorityConfig) -> None:
        """Negative bv reduces priority."""
        spec = _make_spec(business_value=-200, story_points=1)
        score = compute_priority(spec, config=priority_config, today=TODAY)
        # base = -200 * 1.0 / 1 = -200.0, age = 27 * 0.5 = 13.5
        assert score == pytest.approx(-186.5)

    def test_zero_business_value(self, priority_config: PriorityConfig) -> None:
        """Zero bv means base component is 0."""
        spec = _make_spec(business_value=0, story_points=5)
        score = compute_priority(spec, config=priority_config, today=TODAY)
        # base = 0, age = 27 * 0.5 = 13.5
        assert score == pytest.approx(13.5)

    def test_none_business_value(self, priority_config: PriorityConfig) -> None:
        """None bv treated as 0."""
        spec = _make_spec(business_value=None, story_points=5)
        score = compute_priority(spec, config=priority_config, today=TODAY)
        # base = 0, age = 27 * 0.5 = 13.5
        assert score == pytest.approx(13.5)

    def test_graph_dependents(self, priority_config: PriorityConfig) -> None:
        """Unblocks bonus scales with number of dependents."""
        spec = _make_spec(business_value=0, story_points=1, created=TODAY)
        graph = MockGraph({"TST-001": ["TST-002", "TST-003", "TST-004"]})
        score = compute_priority(spec, graph=graph, config=priority_config, today=TODAY)
        # base = 0, unblocks = 50.0 * 3 = 150.0, age = 0
        assert score == pytest.approx(150.0)

    def test_age_bonus(self, priority_config: PriorityConfig) -> None:
        """Anti-starvation bonus grows with age."""
        spec = _make_spec(business_value=0, story_points=1, created=date(2026, 2, 26))
        score = compute_priority(spec, config=priority_config, today=TODAY)
        # age = 30 days * 0.5 = 15.0
        assert score == pytest.approx(15.0)

    def test_future_created_clamped(self, priority_config: PriorityConfig) -> None:
        """Created date in the future produces 0 age bonus."""
        spec = _make_spec(business_value=0, story_points=1, created=date(2026, 4, 1))
        score = compute_priority(spec, config=priority_config, today=TODAY)
        assert score == pytest.approx(0.0)

    def test_all_defaults(self) -> None:
        """compute_priority works with no explicit config or today."""
        spec = _make_spec()
        score = compute_priority(spec)
        assert isinstance(score, float)

    def test_custom_weights(self) -> None:
        """Custom weight values are respected."""
        config = PriorityConfig(
            weights=PriorityWeights(
                business_value=2.0,
                age_bonus_per_day=0.0,
            )
        )
        spec = _make_spec(business_value=100, story_points=5)
        score = compute_priority(spec, config=config, today=TODAY)
        # base = 100 * 2.0 / 5 = 40.0, age = 0
        assert score == pytest.approx(40.0)

    def test_combined_factors(self, priority_config: PriorityConfig) -> None:
        """All factors contribute to the final score."""
        spec = _make_spec(
            business_value=100,
            story_points=5,
            created=date(2026, 3, 18),
            due_date=date(2026, 3, 30),  # 2 days remaining → critical
        )
        graph = MockGraph({"TST-001": ["TST-002"]})
        score = compute_priority(spec, graph=graph, config=priority_config, today=TODAY)
        # base = 100 * 1.0 / 5 = 20.0
        # unblocks = 50.0 * 1 = 50.0
        # age = 10 * 0.5 = 5.0
        # urgency = 200.0 (critical)
        assert score == pytest.approx(275.0)


# ---------------------------------------------------------------------------
# TestDueDateUrgency
# ---------------------------------------------------------------------------


class TestDueDateUrgency:
    """Tests for _compute_due_date_urgency()."""

    def test_no_due_date(self) -> None:
        assert _compute_due_date_urgency(None, TODAY, DueDateUrgency()) == 0.0

    def test_overdue(self) -> None:
        """Past due date → critical bonus."""
        assert _compute_due_date_urgency(
            date(2026, 3, 25), TODAY, DueDateUrgency()
        ) == pytest.approx(200.0)

    def test_critical_range(self) -> None:
        """1 day remaining → critical bonus."""
        assert _compute_due_date_urgency(
            date(2026, 3, 29), TODAY, DueDateUrgency()
        ) == pytest.approx(200.0)

    def test_critical_boundary(self) -> None:
        """Exactly critical_days remaining → critical bonus."""
        assert _compute_due_date_urgency(
            date(2026, 3, 31),
            TODAY,
            DueDateUrgency(),  # 3 days
        ) == pytest.approx(200.0)

    def test_warning_range(self) -> None:
        """5 days remaining → warning bonus."""
        assert _compute_due_date_urgency(
            date(2026, 4, 2), TODAY, DueDateUrgency()
        ) == pytest.approx(50.0)

    def test_warning_boundary(self) -> None:
        """Exactly warning_days remaining → warning bonus."""
        assert _compute_due_date_urgency(
            date(2026, 4, 4),
            TODAY,
            DueDateUrgency(),  # 7 days
        ) == pytest.approx(50.0)

    def test_beyond_warning(self) -> None:
        """8 days remaining → no bonus."""
        assert _compute_due_date_urgency(
            date(2026, 4, 5), TODAY, DueDateUrgency()
        ) == pytest.approx(0.0)

    def test_due_today(self) -> None:
        """Due date == today → 0 days remaining → critical bonus."""
        assert _compute_due_date_urgency(
            TODAY, TODAY, DueDateUrgency()
        ) == pytest.approx(200.0)

    def test_custom_thresholds(self) -> None:
        """Custom urgency config is respected."""
        urgency = DueDateUrgency(
            critical_days=1,
            warning_days=3,
            critical_bonus=500.0,
            warning_bonus=100.0,
        )
        # 2 days remaining: within warning (3) but beyond critical (1)
        assert _compute_due_date_urgency(
            date(2026, 3, 30), TODAY, urgency
        ) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# TestRankSpecs
# ---------------------------------------------------------------------------


class TestRankSpecs:
    """Tests for rank_specs()."""

    def test_sorts_descending(self, priority_config: PriorityConfig) -> None:
        """Specs returned highest-priority first."""
        specs = [
            _make_spec("TST-001", business_value=50, story_points=1, created=TODAY),
            _make_spec("TST-002", business_value=200, story_points=1, created=TODAY),
            _make_spec("TST-003", business_value=100, story_points=1, created=TODAY),
        ]
        ranked = rank_specs(specs, config=priority_config, today=TODAY)
        assert [s.meta.id for s in ranked] == ["TST-002", "TST-003", "TST-001"]

    def test_mutates_priority_score(self, priority_config: PriorityConfig) -> None:
        """rank_specs sets priority_score on each spec."""
        specs = [_make_spec(business_value=100, story_points=1, created=TODAY)]
        rank_specs(specs, config=priority_config, today=TODAY)
        assert specs[0].priority_score == pytest.approx(100.0)

    def test_empty_list(self, priority_config: PriorityConfig) -> None:
        assert rank_specs([], config=priority_config, today=TODAY) == []

    def test_single_spec(self, priority_config: PriorityConfig) -> None:
        specs = [_make_spec(created=TODAY)]
        ranked = rank_specs(specs, config=priority_config, today=TODAY)
        assert len(ranked) == 1

    def test_blocked_specs_included(self, priority_config: PriorityConfig) -> None:
        """Blocked specs are scored and returned, not filtered."""
        spec = _make_spec(business_value=100, story_points=1, created=TODAY)
        spec.is_blocked = True
        ranked = rank_specs([spec], config=priority_config, today=TODAY)
        assert len(ranked) == 1
        assert ranked[0].is_blocked is True

    def test_blocking_task_ranks_higher(self, priority_config: PriorityConfig) -> None:
        """A task that unblocks others ranks above an isolated task of equal value."""
        isolated = _make_spec(
            "TST-001", business_value=100, story_points=1, created=TODAY
        )
        blocker = _make_spec(
            "TST-002", business_value=100, story_points=1, created=TODAY
        )
        graph = MockGraph({"TST-002": ["TST-003", "TST-004"]})
        ranked = rank_specs(
            [isolated, blocker], graph=graph, config=priority_config, today=TODAY
        )
        assert ranked[0].meta.id == "TST-002"


# ---------------------------------------------------------------------------
# TestDependencyLookupProtocol
# ---------------------------------------------------------------------------


class TestDependencyLookupProtocol:
    """Tests for the DependencyLookup protocol."""

    def test_mock_graph_satisfies_protocol(self) -> None:
        graph = MockGraph()
        assert isinstance(graph, DependencyLookup)

    def test_none_graph_zero_bonus(self, priority_config: PriorityConfig) -> None:
        """No graph → dependents_count = 0."""
        spec = _make_spec(business_value=0, story_points=1, created=TODAY)
        score = compute_priority(spec, graph=None, config=priority_config, today=TODAY)
        assert score == pytest.approx(0.0)
