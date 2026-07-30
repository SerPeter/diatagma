"""Tests for core.graph_render — mermaid and tree renderers."""

from datetime import date

from diatagma.core.graph import SpecGraph
from diatagma.core.graph_render import to_mermaid, to_tree
from diatagma.core.models import Spec, SpecLinks, SpecMeta


def _spec(spec_id: str, status: str = "pending", blocked_by=None, relates_to=None):
    return Spec(
        meta=SpecMeta(
            id=spec_id,
            title=spec_id,
            type="feature",
            status=status,
            created=date(2026, 3, 27),
            links=SpecLinks(blocked_by=blocked_by or [], relates_to=relates_to or []),
        )
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
