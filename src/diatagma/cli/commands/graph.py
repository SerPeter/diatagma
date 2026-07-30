"""Graph command — export dependency graph."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json
from diatagma.cli.state import GlobalState
from diatagma.core.graph import _spec_location
from diatagma.core.graph_render import to_mermaid, to_tree
from diatagma.core.models import Spec


def _scope_ids(
    all_specs: list[Spec], *, backlog: bool, archive: bool, full: bool
) -> set[str]:
    """Select which spec IDs are visible in the graph.

    Default: active (root ``.specs/``) specs plus backlog items that block an
    active spec. Flags widen the scope; ``--full`` includes everything. The
    graph itself is always built over the full corpus so blocker statuses are
    known — this only decides what is drawn.
    """
    if full:
        return {s.meta.id for s in all_specs}

    locations = {s.meta.id: _spec_location(s) for s in all_specs}
    active = [s for s in all_specs if locations[s.meta.id] == "active"]
    scope = {s.meta.id for s in active}

    if backlog:
        scope |= {sid for sid, loc in locations.items() if loc == "backlog"}
    if archive:
        scope |= {sid for sid, loc in locations.items() if loc == "archived"}

    # Always pull in backlog items that block an active spec.
    for spec in active:
        for blocker in spec.meta.links.blocked_by:
            if locations.get(blocker) == "backlog":
                scope.add(blocker)

    return scope


def _filter_scope(data: dict, visible: set[str]) -> dict:
    """Restrict a graph dict to visible nodes and the edges among them."""
    nodes = [n for n in data["nodes"] if n["id"] in visible]
    edges = [
        e for e in data["edges"] if e["source"] in visible and e["target"] in visible
    ]
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
    visible = _scope_ids(all_specs, backlog=backlog, archive=archive, full=full)

    if format == "mermaid":
        typer.echo(to_mermaid(ctx.graph, terminal, visible))
    elif format == "tree":
        typer.echo(to_tree(ctx.graph, terminal, visible))
    elif format == "dot":
        typer.echo(_to_dot(_filter_scope(ctx.graph.to_dict(), visible)))
    else:
        print_json(_filter_scope(ctx.graph.to_dict(), visible))


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
