"""Global CLI state shared across commands."""

from __future__ import annotations

from pathlib import Path

from diatagma.core.context import DiatagmaContext, create_context


class GlobalState:
    """Mutable module-level state set by the typer callback."""

    specs_dir: Path = Path.cwd() / ".specs"
    json: bool = False
    quiet: bool = False
    no_color: bool = False

    _ctx: DiatagmaContext | None = None

    @classmethod
    def get_context(cls) -> DiatagmaContext:
        """Lazily create and cache a DiatagmaContext."""
        if cls._ctx is None:
            cls._ctx = create_context(cls.specs_dir)
        return cls._ctx

    @classmethod
    def reset(cls) -> None:
        """Reset cached context (for testing)."""
        cls._ctx = None
