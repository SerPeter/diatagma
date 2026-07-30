"""Human-readable renderings of the dependency graph.

Pure functions over a built :class:`SpecGraph` so any interface (CLI, web,
MCP) can render the same structure. ``to_mermaid`` emits a Mermaid
flowchart; ``to_tree`` emits a topologically-ordered ASCII tree of the
blocking dependencies.

Both accept a ``visible`` node set (the scope) — only those nodes and the
edges among them are drawn — mark node location (``[backlog]`` /
``[archived]``), and draw only *live* blocking edges: a blocker that is
already terminal is a satisfied, not a current, constraint, so its edge is
omitted. The graph is built over the full corpus so blocker statuses are
always known.
"""

from __future__ import annotations

from collections.abc import Iterable

from diatagma.core.graph import SpecGraph
from diatagma.core.models import DEFAULT_TERMINAL_STATUSES

_BLOCKING = "blocked_by"
_DEFAULT_TERMINAL = frozenset(DEFAULT_TERMINAL_STATUSES)


def _safe_id(spec_id: str) -> str:
    """Sanitize a spec ID for use as a Mermaid node identifier."""
    return spec_id.replace("-", "_")


def _loc_suffix(location: str) -> str:
    """Render a location marker for non-active specs."""
    if location == "backlog":
        return " [backlog]"
    if location == "archived":
        return " [archived]"
    return ""


def _visible_set(data: dict, visible: Iterable[str] | None) -> set[str]:
    return {n["id"] for n in data["nodes"]} if visible is None else set(visible)


def _nodes_in_cycles(children: dict[str, list[str]]) -> set[str]:
    """Nodes on a cycle within the given adjacency (the edges actually drawn).

    Cycles are detected over the live, in-scope blocking edges — not the full
    graph — so a loop already broken by a done blocker isn't mislabelled.
    """
    white, grey, black = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(children, white)
    on_cycle: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> None:
        color[node] = grey
        path.append(node)
        for nxt in children.get(node, []):
            state = color.get(nxt, black)
            if state == grey:
                on_cycle.update(path[path.index(nxt) :])
            elif state == white:
                visit(nxt)
        path.pop()
        color[node] = black

    for node in children:
        if color[node] == white:
            visit(node)
    return on_cycle


def to_mermaid(
    graph: SpecGraph,
    terminal_statuses: frozenset[str] = _DEFAULT_TERMINAL,
    visible: Iterable[str] | None = None,
) -> str:
    """Render the scoped graph as a Mermaid ``flowchart TD``.

    Only nodes in ``visible`` and edges among them are drawn. Live blocking
    edges are solid; other typed edges are dotted and labelled. Blocking edges
    whose blocker is already terminal are omitted (satisfied).
    """
    data = graph.to_dict()
    vis = _visible_set(data, visible)
    status = {n["id"]: n["status"] for n in data["nodes"]}
    lines = ["flowchart TD"]
    for node in data["nodes"]:
        if node["id"] not in vis:
            continue
        label = f"{node['id']} ({node['status']}){_loc_suffix(node['location'])}"
        lines.append(f'    {_safe_id(node["id"])}["{label}"]')
    for edge in data["edges"]:
        if edge["source"] not in vis or edge["target"] not in vis:
            continue
        src = _safe_id(edge["source"])
        tgt = _safe_id(edge["target"])
        if edge["type"] == _BLOCKING:
            if status.get(edge["source"]) in terminal_statuses:
                continue  # satisfied blocker — not a live constraint
            lines.append(f"    {src} --> {tgt}")
        else:
            lines.append(f"    {src} -.{edge['type']}.-> {tgt}")
    return "\n".join(lines)


def to_tree(
    graph: SpecGraph,
    terminal_statuses: frozenset[str] = _DEFAULT_TERMINAL,
    visible: Iterable[str] | None = None,
) -> str:
    """Render *live* blocking dependencies among ``visible`` specs as a tree.

    Each unsatisfied blocker parents the specs it blocks; a blocker that is
    already terminal is dropped, so its dependents surface as roots. Nodes in a
    dependency cycle are marked ``(cycle)`` instead of crashing.
    """
    data = graph.to_dict()
    vis = _visible_set(data, visible)
    status = {n["id"]: n["status"] for n in data["nodes"]}
    location = {n["id"]: n["location"] for n in data["nodes"]}

    children: dict[str, list[str]] = {i: [] for i in vis}
    indegree: dict[str, int] = {i: 0 for i in vis}
    for edge in data["edges"]:
        if edge["type"] != _BLOCKING:
            continue
        src, tgt = edge["source"], edge["target"]
        if src not in vis or tgt not in vis:
            continue
        if status.get(src) in terminal_statuses:
            continue  # satisfied blocker — omit the edge
        children[src].append(tgt)
        indegree[tgt] += 1

    cycle_nodes = _nodes_in_cycles(children)

    lines: list[str] = []
    expanded: set[str] = set()

    def walk(node: str, depth: int) -> None:
        cycle = " (cycle)" if node in cycle_nodes else ""
        loc = _loc_suffix(location.get(node, "unknown"))
        indent = "  " * depth
        lines.append(f"{indent}- {node} [{status.get(node, '?')}]{loc}{cycle}")
        if node in expanded:
            return
        expanded.add(node)
        for child in sorted(children.get(node, [])):
            walk(child, depth + 1)

    for root in sorted(n for n, deg in indegree.items() if deg == 0):
        walk(root, 0)
    # Cycle-locked components have no zero-indegree root; surface them too.
    for node in sorted(vis):
        if node not in expanded:
            walk(node, 0)

    return "\n".join(lines) if lines else "(no specs)"


__all__ = ["to_mermaid", "to_tree"]
