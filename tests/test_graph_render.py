"""Tests for core.graph_render — mermaid and tree renderers."""

from datetime import date
from pathlib import Path

from diatagma.core.graph import SpecGraph
from diatagma.core.graph_render import to_mermaid, to_tree
from diatagma.core.models import Spec, SpecLinks, SpecMeta


def _spec(
    spec_id: str,
    status: str = "pending",
    blocked_by=None,
    relates_to=None,
    location: str = "active",
):
    root = Path(".specs")
    dir_ = {"backlog": root / "backlog", "archived": root / "archive"}.get(
        location, root
    )
    return Spec(
        meta=SpecMeta(
            id=spec_id,
            title=spec_id,
            type="feature",
            status=status,
            created=date(2026, 3, 27),
            links=SpecLinks(blocked_by=blocked_by or [], relates_to=relates_to or []),
        ),
        file_path=dir_ / f"{spec_id}-x.story.md",
    )


def _graph(specs):
    graph = SpecGraph()
    graph.build(specs)
    return graph


class TestMermaid:
    def test_has_flowchart_header(self):
        out = to_mermaid(_graph([_spec("DIA-001")]))
        assert out.startswith("flowchart TD")

    def test_node_label_has_id_and_status(self):
        out = to_mermaid(_graph([_spec("DIA-001", status="done")]))
        assert 'DIA_001["DIA-001 (done)"]' in out

    def test_blocking_edge_solid(self):
        specs = [_spec("DIA-001"), _spec("DIA-002", blocked_by=["DIA-001"])]
        out = to_mermaid(_graph(specs))
        assert "DIA_001 --> DIA_002" in out

    def test_non_blocking_edge_dotted(self):
        specs = [_spec("DIA-001", relates_to=["DIA-002"]), _spec("DIA-002")]
        out = to_mermaid(_graph(specs))
        assert "-.relates_to.->" in out


class TestTree:
    def test_topological_order(self):
        specs = [_spec("DIA-001"), _spec("DIA-002", blocked_by=["DIA-001"])]
        out = to_tree(_graph(specs))
        lines = out.splitlines()
        # blocker appears before (and less indented than) its dependent
        assert lines[0].strip() == "- DIA-001 [pending]"
        assert any(line.startswith("  - DIA-002") for line in lines)

    def test_empty(self):
        assert to_tree(_graph([])) == "(no specs)"

    def test_cycle_marked_not_crash(self):
        specs = [
            _spec("DIA-001", blocked_by=["DIA-002"]),
            _spec("DIA-002", blocked_by=["DIA-001"]),
        ]
        out = to_tree(_graph(specs))
        assert "(cycle)" in out


class TestScopeAndMarkers:
    def test_visible_filters_nodes(self):
        graph = _graph([_spec("DIA-001"), _spec("DIA-002"), _spec("DIA-003")])
        out = to_tree(graph, visible={"DIA-001", "DIA-002"})
        assert "DIA-001" in out
        assert "DIA-002" in out
        assert "DIA-003" not in out

    def test_satisfied_blocker_edge_dropped(self):
        # A is done → its blocking edge to B is omitted; B surfaces as a root.
        graph = _graph(
            [
                _spec("DIA-001", status="done"),
                _spec("DIA-002", status="pending", blocked_by=["DIA-001"]),
            ]
        )
        out = to_tree(graph, terminal_statuses=frozenset({"done", "cancelled"}))
        lines = out.splitlines()
        # DIA-002 is not indented under DIA-001 (edge dropped)
        assert any(line == "- DIA-002 [pending]" for line in lines)

    def test_live_blocker_edge_kept(self):
        graph = _graph(
            [
                _spec("DIA-001", status="pending"),
                _spec("DIA-002", status="pending", blocked_by=["DIA-001"]),
            ]
        )
        out = to_mermaid(graph)
        assert "DIA_001 --> DIA_002" in out

    def test_location_marker_tree(self):
        graph = _graph([_spec("DIA-001", location="backlog")])
        assert "[backlog]" in to_tree(graph)

    def test_location_marker_mermaid(self):
        graph = _graph([_spec("DIA-001", location="archived")])
        assert "[archived]" in to_mermaid(graph)


class TestCycleFromDrawnEdges:
    def test_done_broken_cycle_not_marked(self):
        # A is done → its edge is dropped, breaking the drawn cycle.
        graph = _graph(
            [
                _spec("DIA-001", status="done", blocked_by=["DIA-002"]),
                _spec("DIA-002", status="pending", blocked_by=["DIA-001"]),
            ]
        )
        out = to_tree(graph, terminal_statuses=frozenset({"done", "cancelled"}))
        assert "(cycle)" not in out

    def test_live_cycle_still_marked(self):
        graph = _graph(
            [
                _spec("DIA-001", status="pending", blocked_by=["DIA-002"]),
                _spec("DIA-002", status="pending", blocked_by=["DIA-001"]),
            ]
        )
        assert "(cycle)" in to_tree(graph)
