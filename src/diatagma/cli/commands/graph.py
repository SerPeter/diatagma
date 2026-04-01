"""Graph command — export dependency graph."""

from __future__ import annotations

from typing import Annotated

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_json
from diatagma.cli.state import GlobalState


@app.command()
def graph(
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json or dot."),
    ] = "json",
) -> None:
    """Export the dependency graph."""
    ctx = GlobalState.get_context()
    ctx.refresh_graph()
    data = ctx.graph.to_dict()

    if format == "dot":
        typer.echo(_to_dot(data))
    else:
        print_json(data)


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
