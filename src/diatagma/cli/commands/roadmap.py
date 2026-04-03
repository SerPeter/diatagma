"""Roadmap command — generate ROADMAP.md from current spec state."""

from __future__ import annotations


from diatagma.cli.app import app
from diatagma.cli.output import print_json, print_success
from diatagma.cli.state import GlobalState
from diatagma.core.roadmap import (
    generate_roadmap,
    generate_roadmap_json,
    update_roadmap_file,
)


@app.command()
def roadmap() -> None:
    """Generate or update ROADMAP.md from current spec state."""
    ctx = GlobalState.get_context()

    if GlobalState.json:
        data = generate_roadmap_json(ctx.store, ctx.config)
        print_json(data)
        return

    roadmap_path = ctx.config.specs_dir / "ROADMAP.md"

    if roadmap_path.exists():
        existing = roadmap_path.read_text(encoding="utf-8")
        content = update_roadmap_file(existing, ctx.store, ctx.config)
    else:
        content = generate_roadmap(ctx.store, ctx.config)

    roadmap_path.write_text(content, encoding="utf-8")
    print_success(f"Roadmap written to {roadmap_path}")
