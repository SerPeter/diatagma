"""Dependency graph powered by networkx.

Builds a DAG of spec relationships from ``SpecLinks`` declarations.
Provides cycle detection, topological sorting, blocked/unblocked status
computation, and typed relationship queries.

Edge direction convention:
    If DIA-020 declares ``blocked_by: [DIA-014]``, the graph stores an
    edge ``DIA-014 → DIA-020`` (blocker points to dependent). This way
    ``nx.successors()`` yields dependents and topological sort naturally
    orders dependencies before the specs that need them.

Key class:
    SpecGraph
        .build(specs)
        .is_blocked(spec_id)     → bool
        .get_unblocked()         → list[str]
        .get_blockers(spec_id)   → list[str]
        .get_dependents(spec_id) → list[str]
        .get_related(spec_id)    → list[str]
        .get_superseded()        → list[str]
        .topological_sort()      → list[str]
        .detect_cycles()         → list[list[str]]
        .to_dict()               → dict
"""

from __future__ import annotations

from enum import Enum

import networkx as nx

from diatagma.core.models import Spec

# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------

_DONE_STATUSES = frozenset({"done", "cancelled"})


class EdgeType(str, Enum):
    """Typed relationship between two specs."""

    BLOCKED_BY = "blocked_by"
    RELATES_TO = "relates_to"
    SUPERSEDES = "supersedes"
    DISCOVERED_FROM = "discovered_from"


# ---------------------------------------------------------------------------
# SpecGraph
# ---------------------------------------------------------------------------


class SpecGraph:
    """Directed graph of spec relationships.

    Satisfies the ``DependencyLookup`` protocol from ``priority.py``
    via :meth:`get_dependents`.
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    # --- Build -------------------------------------------------------------

    def build(self, specs: list[Spec]) -> None:
        """Populate the graph from a list of specs.

        Clears any existing data first. Nodes carry a ``status`` attribute;
        edges carry an ``edge_type`` attribute.
        """
        self._graph.clear()

        for spec in specs:
            self._graph.add_node(spec.meta.id, status=spec.meta.status)

        for spec in specs:
            sid = spec.meta.id
            links = spec.meta.links

            for blocker in links.blocked_by:
                self._ensure_node(blocker)
                self._graph.add_edge(blocker, sid, edge_type=EdgeType.BLOCKED_BY)

            for related in links.relates_to:
                self._ensure_node(related)
                self._graph.add_edge(sid, related, edge_type=EdgeType.RELATES_TO)

            for superseded in links.supersedes:
                self._ensure_node(superseded)
                self._graph.add_edge(sid, superseded, edge_type=EdgeType.SUPERSEDES)

            if links.discovered_from is not None:
                self._ensure_node(links.discovered_from)
                self._graph.add_edge(
                    links.discovered_from, sid, edge_type=EdgeType.DISCOVERED_FROM
                )

    # --- Blocking queries --------------------------------------------------

    def get_dependents(self, spec_id: str) -> list[str]:
        """Specs that declare ``blocked_by`` this spec (successors)."""
        if spec_id not in self._graph:
            return []
        return [
            target
            for target in self._graph.successors(spec_id)
            if self._edge_type(spec_id, target) == EdgeType.BLOCKED_BY
        ]

    def get_blockers(self, spec_id: str) -> list[str]:
        """Specs that this spec declares as blockers (predecessors)."""
        if spec_id not in self._graph:
            return []
        return [
            source
            for source in self._graph.predecessors(spec_id)
            if self._edge_type(source, spec_id) == EdgeType.BLOCKED_BY
        ]

    def is_blocked(
        self, spec_id: str, done_statuses: frozenset[str] = _DONE_STATUSES
    ) -> bool:
        """True if any blocker has a status not in *done_statuses*."""
        for blocker in self.get_blockers(spec_id):
            status = self._graph.nodes[blocker].get("status", "pending")
            if status not in done_statuses:
                return True
        return False

    def get_unblocked(
        self, done_statuses: frozenset[str] = _DONE_STATUSES
    ) -> list[str]:
        """Spec IDs that are not blocked and not done/cancelled themselves."""
        result: list[str] = []
        for node in self._graph.nodes:
            status = self._graph.nodes[node].get("status", "pending")
            if status in done_statuses:
                continue
            if not self.is_blocked(node, done_statuses):
                result.append(node)
        return sorted(result)

    # --- Relationship queries ----------------------------------------------

    def get_related(self, spec_id: str) -> list[str]:
        """Specs that declare ``relates_to`` this spec (inverse lookup)."""
        if spec_id not in self._graph:
            return []
        return [
            source
            for source in self._graph.predecessors(spec_id)
            if self._edge_type(source, spec_id) == EdgeType.RELATES_TO
        ]

    def get_superseded(self) -> list[str]:
        """All spec IDs that are targets of ``supersedes`` edges."""
        superseded: set[str] = set()
        for u, v, data in self._graph.edges(data=True):
            if data.get("edge_type") == EdgeType.SUPERSEDES:
                superseded.add(v)
        return sorted(superseded)

    # --- DAG analysis (blocking edges only) --------------------------------

    def detect_cycles(self) -> list[list[str]]:
        """Find cycles in the blocking subgraph.

        Returns a list of cycles, where each cycle is a list of spec IDs.
        Non-blocking edges (relates_to, etc.) are excluded.
        """
        sub = self._blocking_subgraph()
        return list(nx.simple_cycles(sub))

    def topological_sort(self) -> list[str]:
        """Topological ordering of the blocking subgraph.

        Raises ``nx.NetworkXUnfeasible`` if cycles exist.
        """
        sub = self._blocking_subgraph()
        return list(nx.topological_sort(sub))

    # --- Export ------------------------------------------------------------

    def to_dict(self) -> dict:
        """JSON-serializable export of nodes and typed edges."""
        nodes = []
        for node_id, data in self._graph.nodes(data=True):
            nodes.append({"id": node_id, "status": data.get("status", "unknown")})

        edges = []
        for u, v, data in self._graph.edges(data=True):
            edge_type = data.get("edge_type", "unknown")
            edges.append(
                {
                    "source": u,
                    "target": v,
                    "type": edge_type.value
                    if isinstance(edge_type, EdgeType)
                    else str(edge_type),
                }
            )

        return {"nodes": nodes, "edges": edges}

    # --- Internal helpers --------------------------------------------------

    def _ensure_node(self, spec_id: str) -> None:
        """Add a node if it doesn't exist (for referenced but unseen specs)."""
        if spec_id not in self._graph:
            self._graph.add_node(spec_id, status="unknown")

    def _edge_type(self, source: str, target: str) -> EdgeType | None:
        """Get the edge type between two nodes, or None."""
        data = self._graph.get_edge_data(source, target)
        if data is None:
            return None
        return data.get("edge_type")

    def _blocking_subgraph(self) -> nx.DiGraph:
        """Return a subgraph containing only BLOCKED_BY edges."""
        edges = [
            (u, v)
            for u, v, data in self._graph.edges(data=True)
            if data.get("edge_type") == EdgeType.BLOCKED_BY
        ]
        sub = nx.DiGraph()
        sub.add_nodes_from(self._graph.nodes)
        sub.add_edges_from(edges)
        return sub


__all__ = [
    "EdgeType",
    "SpecGraph",
]
