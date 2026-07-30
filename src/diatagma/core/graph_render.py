"""Human-readable renderings of the dependency graph.

Pure functions over a built :class:`SpecGraph` so any interface (CLI, web,
MCP) can render the same structure. ``to_mermaid`` emits a Mermaid
flowchart; ``to_tree`` emits a topologically-ordered ASCII tree of the
blocking dependencies.
"""

from __future__ import annotations

from diatagma.core.graph import SpecGraph

_BLOCKING = "blocked_by"


def _safe_id(spec_id: str) -> str:
    """Sanitize a spec ID for use as a Mermaid node identifier."""
    return spec_id.replace("-", "_")


def to_mermaid(graph: SpecGraph) -> str:
    """Render the graph as a Mermaid ``flowchart TD``.

    Blocking edges are solid; other typed edges (relates_to, supersedes,
    discovered_from) are dotted and labelled with their type.
    """
    data = graph.to_dict()
    lines = ["flowchart TD"]
    for node in data["nodes"]:
        lines.append(f'    {_safe_id(node["id"])}["{node["id"]} ({node["status"]})"]')
    for edge in data["edges"]:
        src = _safe_id(edge["source"])
        tgt = _safe_id(edge["target"])
        if edge["type"] == _BLOCKING:
            lines.append(f"    {src} --> {tgt}")
        else:
            lines.append(f"    {src} -.{edge['type']}.-> {tgt}")
    return "\n".join(lines)


def to_tree(graph: SpecGraph) -> str:
    """Render blocking dependencies as an indented, topologically-first tree.

    Each blocker parents the specs it blocks. Nodes participating in a
    dependency cycle are marked ``(cycle)`` instead of crashing.
    """
    data = graph.to_dict()
    status = {n["id"]: n["status"] for n in data["nodes"]}

    children: dict[str, list[str]] = {n["id"]: [] for n in data["nodes"]}
    indegree: dict[str, int] = {n["id"]: 0 for n in data["nodes"]}
    for edge in data["edges"]:
        if edge["type"] != _BLOCKING:
            continue
        children[edge["source"]].append(edge["target"])
        indegree[edge["target"]] += 1

    cycle_nodes = {sid for cycle in graph.detect_cycles() for sid in cycle}

    lines: list[str] = []
    expanded: set[str] = set()

    def walk(node: str, depth: int) -> None:
        marker = " (cycle)" if node in cycle_nodes else ""
        indent = "  " * depth
        lines.append(f"{indent}- {node} [{status.get(node, '?')}]{marker}")
        if node in expanded:
            return
        expanded.add(node)
        for child in sorted(children.get(node, [])):
            walk(child, depth + 1)

    for root in sorted(n for n, deg in indegree.items() if deg == 0):
        walk(root, 0)
    # Cycle-locked components have no zero-indegree root; surface them too.
    for node in sorted(status):
        if node not in expanded:
            walk(node, 0)

    return "\n".join(lines) if lines else "(no specs)"


__all__ = ["to_mermaid", "to_tree"]
