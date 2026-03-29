"""Tests for core.graph — DAG construction, typed edges, cycle detection."""

from datetime import date

import networkx as nx
import pytest

from diatagma.core.graph import SpecGraph
from diatagma.core.models import Spec, SpecBody, SpecLinks, SpecMeta
from diatagma.core.priority import DependencyLookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(
    spec_id: str,
    status: str = "pending",
    blocked_by: list[str] | None = None,
    relates_to: list[str] | None = None,
    supersedes: list[str] | None = None,
    discovered_from: str | None = None,
) -> Spec:
    """Build a minimal Spec with specified links."""
    links = SpecLinks(
        blocked_by=blocked_by or [],
        relates_to=relates_to or [],
        supersedes=supersedes or [],
        discovered_from=discovered_from,
    )
    meta = SpecMeta(
        id=spec_id,
        title=f"Spec {spec_id}",
        type="feature",
        status=status,
        links=links,
        created=date(2026, 3, 27),
    )
    return Spec(meta=meta, body=SpecBody())


# ===========================================================================
# TestBuild
# ===========================================================================


class TestBuild:
    """Graph construction from spec lists."""

    def test_empty_build(self):
        g = SpecGraph()
        g.build([])
        assert g.to_dict()["nodes"] == []

    def test_single_spec_no_links(self):
        g = SpecGraph()
        g.build([_spec("DIA-001")])
        export = g.to_dict()
        assert len(export["nodes"]) == 1
        assert len(export["edges"]) == 0

    def test_blocked_by_creates_edge(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", blocked_by=["DIA-001"]),
            ]
        )
        export = g.to_dict()
        assert len(export["edges"]) == 1
        edge = export["edges"][0]
        assert edge["source"] == "DIA-001"
        assert edge["target"] == "DIA-002"
        assert edge["type"] == "blocked_by"

    def test_rebuild_clears_previous(self):
        g = SpecGraph()
        g.build([_spec("DIA-001"), _spec("DIA-002", blocked_by=["DIA-001"])])
        g.build([_spec("DIA-003")])
        export = g.to_dict()
        assert len(export["nodes"]) == 1
        assert len(export["edges"]) == 0

    def test_referenced_but_unseen_spec_gets_unknown_status(self):
        g = SpecGraph()
        g.build([_spec("DIA-002", blocked_by=["DIA-001"])])
        export = g.to_dict()
        node_map = {n["id"]: n["status"] for n in export["nodes"]}
        assert node_map["DIA-001"] == "unknown"
        assert node_map["DIA-002"] == "pending"


# ===========================================================================
# TestBlockingQueries
# ===========================================================================


class TestBlockingQueries:
    """get_dependents, get_blockers, is_blocked, get_unblocked."""

    @pytest.fixture
    def graph(self) -> SpecGraph:
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", status="done"),
                _spec("DIA-002", status="pending", blocked_by=["DIA-001"]),
                _spec("DIA-003", status="pending", blocked_by=["DIA-001", "DIA-002"]),
            ]
        )
        return g

    def test_get_dependents(self, graph: SpecGraph):
        deps = graph.get_dependents("DIA-001")
        assert set(deps) == {"DIA-002", "DIA-003"}

    def test_get_dependents_leaf(self, graph: SpecGraph):
        assert graph.get_dependents("DIA-003") == []

    def test_get_dependents_unknown_id(self, graph: SpecGraph):
        assert graph.get_dependents("NOPE-999") == []

    def test_get_blockers(self, graph: SpecGraph):
        blockers = graph.get_blockers("DIA-003")
        assert set(blockers) == {"DIA-001", "DIA-002"}

    def test_get_blockers_root(self, graph: SpecGraph):
        assert graph.get_blockers("DIA-001") == []

    def test_is_blocked_all_blockers_done(self, graph: SpecGraph):
        # DIA-002 blocked by DIA-001 which is done
        assert graph.is_blocked("DIA-002") is False

    def test_is_blocked_some_blockers_pending(self, graph: SpecGraph):
        # DIA-003 blocked by DIA-001 (done) and DIA-002 (pending)
        assert graph.is_blocked("DIA-003") is True

    def test_is_blocked_no_blockers(self, graph: SpecGraph):
        assert graph.is_blocked("DIA-001") is False

    def test_get_unblocked(self, graph: SpecGraph):
        # DIA-001 is done (excluded), DIA-002 is unblocked, DIA-003 is blocked
        assert graph.get_unblocked() == ["DIA-002"]

    def test_get_unblocked_all_done(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", status="done"),
                _spec("DIA-002", status="cancelled"),
            ]
        )
        assert g.get_unblocked() == []

    def test_is_blocked_custom_done_statuses(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", status="archived"),
                _spec("DIA-002", status="pending", blocked_by=["DIA-001"]),
            ]
        )
        # Default done_statuses don't include "archived"
        assert g.is_blocked("DIA-002") is True
        # With custom done_statuses
        assert g.is_blocked("DIA-002", frozenset({"archived"})) is False


# ===========================================================================
# TestRelationshipQueries
# ===========================================================================


class TestRelationshipQueries:
    """get_related and get_superseded."""

    def test_get_related(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", relates_to=["DIA-001"]),
            ]
        )
        assert g.get_related("DIA-001") == ["DIA-002"]

    def test_get_related_no_relations(self):
        g = SpecGraph()
        g.build([_spec("DIA-001")])
        assert g.get_related("DIA-001") == []

    def test_get_related_unknown_id(self):
        g = SpecGraph()
        g.build([])
        assert g.get_related("NOPE-999") == []

    def test_relates_to_does_not_affect_blocking(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", relates_to=["DIA-001"]),
            ]
        )
        assert g.is_blocked("DIA-002") is False

    def test_get_superseded(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002"),
                _spec("DIA-003", supersedes=["DIA-001"]),
            ]
        )
        assert g.get_superseded() == ["DIA-001"]

    def test_get_superseded_multiple(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002"),
                _spec("DIA-003", supersedes=["DIA-001", "DIA-002"]),
            ]
        )
        assert g.get_superseded() == ["DIA-001", "DIA-002"]

    def test_get_superseded_empty(self):
        g = SpecGraph()
        g.build([_spec("DIA-001")])
        assert g.get_superseded() == []

    def test_discovered_from_edge(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", discovered_from="DIA-001"),
            ]
        )
        export = g.to_dict()
        edge = next(e for e in export["edges"] if e["type"] == "discovered_from")
        assert edge["source"] == "DIA-001"
        assert edge["target"] == "DIA-002"


# ===========================================================================
# TestCycleDetection
# ===========================================================================


class TestCycleDetection:
    """Cycle detection on blocking edges only."""

    def test_no_cycles(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", blocked_by=["DIA-001"]),
                _spec("DIA-003", blocked_by=["DIA-002"]),
            ]
        )
        assert g.detect_cycles() == []

    def test_simple_cycle(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", blocked_by=["DIA-002"]),
                _spec("DIA-002", blocked_by=["DIA-001"]),
            ]
        )
        cycles = g.detect_cycles()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"DIA-001", "DIA-002"}

    def test_relates_to_cycle_not_detected(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", relates_to=["DIA-002"]),
                _spec("DIA-002", relates_to=["DIA-001"]),
            ]
        )
        assert g.detect_cycles() == []


# ===========================================================================
# TestTopologicalSort
# ===========================================================================


class TestTopologicalSort:
    """Topological sort on blocking edges."""

    def test_linear_chain(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", blocked_by=["DIA-001"]),
                _spec("DIA-003", blocked_by=["DIA-002"]),
            ]
        )
        order = g.topological_sort()
        assert order.index("DIA-001") < order.index("DIA-002")
        assert order.index("DIA-002") < order.index("DIA-003")

    def test_diamond(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001"),
                _spec("DIA-002", blocked_by=["DIA-001"]),
                _spec("DIA-003", blocked_by=["DIA-001"]),
                _spec("DIA-004", blocked_by=["DIA-002", "DIA-003"]),
            ]
        )
        order = g.topological_sort()
        assert order.index("DIA-001") < order.index("DIA-002")
        assert order.index("DIA-001") < order.index("DIA-003")
        assert order.index("DIA-002") < order.index("DIA-004")
        assert order.index("DIA-003") < order.index("DIA-004")

    def test_cycle_raises(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", blocked_by=["DIA-002"]),
                _spec("DIA-002", blocked_by=["DIA-001"]),
            ]
        )
        with pytest.raises(nx.NetworkXUnfeasible):
            g.topological_sort()


# ===========================================================================
# TestExport
# ===========================================================================


class TestExport:
    """to_dict() JSON export."""

    def test_export_structure(self):
        g = SpecGraph()
        g.build(
            [
                _spec("DIA-001", status="done"),
                _spec("DIA-002", blocked_by=["DIA-001"], relates_to=["DIA-001"]),
            ]
        )
        export = g.to_dict()
        assert "nodes" in export
        assert "edges" in export
        assert len(export["nodes"]) == 2
        assert len(export["edges"]) == 2

        edge_types = {e["type"] for e in export["edges"]}
        assert edge_types == {"blocked_by", "relates_to"}


# ===========================================================================
# TestProtocol
# ===========================================================================


class TestProtocol:
    """SpecGraph satisfies DependencyLookup protocol."""

    def test_satisfies_protocol(self):
        g = SpecGraph()
        assert isinstance(g, DependencyLookup)
