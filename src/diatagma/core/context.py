"""Shared bootstrap — wires up all core objects from a .specs/ directory.

Every interface (CLI, MCP, web) constructs a ``DiatagmaContext`` once
and passes it to command/tool/route handlers. This avoids duplicating
the 10-line bootstrap sequence across layers.

Key function:
    create_context(specs_dir) → DiatagmaContext
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from diatagma.core.changelog import Changelog
from diatagma.core.config import DiatagmaConfig
from diatagma.core.graph import SpecGraph
from diatagma.core.lifecycle import LifecycleEngine
from diatagma.core.models import Spec
from diatagma.core.store import SpecStore


@dataclass(frozen=True)
class DiatagmaContext:
    """All core objects needed by any interface layer."""

    config: DiatagmaConfig
    store: SpecStore
    graph: SpecGraph
    lifecycle: LifecycleEngine
    changelog: Changelog

    def refresh_graph(self, specs: list[Spec] | None = None) -> list[Spec]:
        """Reload specs and rebuild the dependency graph.

        Returns the fresh spec list for convenience.
        """
        all_specs = specs if specs is not None else self.store.list()
        self.graph.build(all_specs)
        return all_specs


def create_context(specs_dir: Path) -> DiatagmaContext:
    """Bootstrap all core objects from a .specs/ directory."""
    config = DiatagmaConfig(specs_dir)
    changelog = Changelog(specs_dir / "changelog.md")
    store = SpecStore(
        specs_dir,
        prefixes=config.prefixes,
        templates=config.templates,
        settings=config.settings,
        on_mutation=changelog,
    )
    graph = SpecGraph()
    lifecycle = LifecycleEngine(store, config.settings)

    return DiatagmaContext(
        config=config,
        store=store,
        graph=graph,
        lifecycle=lifecycle,
        changelog=changelog,
    )


__all__ = [
    "DiatagmaContext",
    "create_context",
]
