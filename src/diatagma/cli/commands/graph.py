"""Graph command — export dependency graph."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json
from diatagma.cli.state import GlobalState
from diatagma.core.graph import SpecGraph
from diatagma.core.graph_render import to_mermaid, to_tree


def _scope_ids(
    graph: SpecGraph,
    terminal: frozenset[str],
    *,
    backlog: bool,
    archive: bool,
    full: bool,
) -> set[str]:
    """Select which spec IDs are visible in the graph.

    Default: active (root ``.specs/``) specs plus **every live blocker** of a
    visible spec, followed transitively — so no unmet constraint is hidden,
    whether it lives in backlog, was archived while still live, or is a dangling
    reference. Flags widen the scope; ``--full`` includes everything. Computed
    from the built graph (which carries status + location for every node,
    including referenced-but-missing ones).
    """
    data = graph.to_dict()
    status = {n["id"]: n["status"] for n in data["nodes"]}
    location = {n["id"]: n["location"] for n in data["nodes"]}

    if full:
        return set(status)

    scope = {nid for nid, loc in location.items() if loc == "active"}
    if backlog:
        scope |= {nid for nid, loc in location.items() if loc == "backlog"}
    if archive:
        scope |= {nid for nid, loc in location.items() if loc == "archived"}

    # Pull in every live (non-terminal) blocker of a visible spec, transitively.
    frontier = list(scope)
    while frontier:
        for blocker in graph.get_blockers(frontier.pop()):
            if status.get(blocker) not in terminal and blocker not in scope:
                scope.add(blocker)
                frontier.append(blocker)

    return scope


def _filter_scope(data: dict, visible: set[str], terminal: frozenset[str]) -> dict:
    """Restrict a graph dict to visible nodes and live edges among them.

    Blocking edges whose blocker is already terminal are dropped (satisfied),
    so json/dot match the tree/mermaid live-edge view.
    """
    status = {n["id"]: n["status"] for n in data["nodes"]}
    nodes = [n for n in data["nodes"] if n["id"] in visible]
    edges = []
    for edge in data["edges"]:
        if edge["source"] not in visible or edge["target"] not in visible:
            continue
        if edge["type"] == "blocked_by" and status.get(edge["source"]) in terminal:
            continue
        edges.append(edge)
    return {"nodes": nodes, "edges": edges}


@app.command()
def graph(
    format: Annotated[
        str,
        typer.Option(
            "--format", "-f", help="Output format: json, mermaid, tree, or dot."
        ),
    ] = "json",
    backlog: Annotated[
        bool, typer.Option("--backlog", help="Also include backlog specs.")
    ] = False,
    archive: Annotated[
        bool, typer.Option("--archive", help="Also include archived specs.")
    ] = False,
    full: Annotated[
        bool, typer.Option("--full", help="Include everything (backlog + archive).")
    ] = False,
) -> None:
    """Export the dependency graph.

    By default only active specs (and backlog items that block them) are shown;
    use --backlog / --archive / --full to widen the scope.
    """
    ctx = GlobalState.get_context()
    all_specs = ctx.store.list(include_archive=True)
    terminal = ctx.config.settings.terminal_status_set
    ctx.graph.build(all_specs, terminal_statuses=terminal)
    visible = _scope_ids(
        ctx.graph, terminal, backlog=backlog, archive=archive, full=full
    )

    if format == "mermaid":
        typer.echo(to_mermaid(ctx.graph, terminal, visible))
    elif format == "tree":
        typer.echo(to_tree(ctx.graph, terminal, visible))
    elif format == "dot":
        typer.echo(_to_dot(_filter_scope(ctx.graph.to_dict(), visible, terminal)))
    else:
        print_json(_filter_scope(ctx.graph.to_dict(), visible, terminal))


def _to_dot(data: dict) -> str:
    """Convert graph dict to Graphviz DOT format."""
    lines = ["digraph specs {", "  rankdir=LR;"]
    for node in data["nodes"]:
        label = f"{node['id']}\\n[{node['status']}]"
        lines.append(f'  "{node["id"]}" [label="{label}"];')
    for edge in data["edges"]:
        style = "style=dashed" if edge["type"] != "blocked_by" else ""
        label = edge["type"]
        attrs = f'label="{label}"'
        if style:
            attrs += f" {style}"
        lines.append(f'  "{edge["source"]}" -> "{edge["target"]}" [{attrs}];')
    lines.append("}")
    return "\n".join(lines)
