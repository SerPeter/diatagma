"""File watcher for live spec change detection.

Monitors the ``.specs/`` directory for spec file changes and dispatches
domain events to registered callbacks. Uses ``watchfiles`` (Rust-based,
cross-platform) for filesystem monitoring with built-in debouncing.

Key classes:
    SpecWatcher        — background thread that monitors .specs/
    SpecFileFilter     — watchfiles filter for spec .md files
    SpecChangeEvent    — domain event for a single file change

Key functions:
    make_cache_callback  — factory for a cache-invalidating callback
    make_notify_callback — factory for a notification-forwarding callback
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Literal, NamedTuple

from loguru import logger
from watchfiles import Change, DefaultFilter, watch

from diatagma.core.cache import SpecCache
from diatagma.core.models import Spec
from diatagma.core.parser import ParseError, parse_spec_file

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SPEC_ID_RE = re.compile(r"^([A-Z]{1,5}-\d{3,})-.+\.\w+\.md$")
"""Extract spec ID from a spec filename."""

_CHANGE_MAP: dict[Change, Literal["added", "modified", "deleted"]] = {
    Change.added: "added",
    Change.modified: "modified",
    Change.deleted: "deleted",
}

# ---------------------------------------------------------------------------
# Domain event
# ---------------------------------------------------------------------------


class SpecChangeEvent(NamedTuple):
    """A single spec file change detected by the watcher."""

    change_type: Literal["added", "modified", "deleted"]
    path: Path
    spec_id: str | None


WatcherCallback = Callable[[list[SpecChangeEvent]], None]
"""Signature for watcher callbacks: receives a batch of change events."""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_spec_id(path: Path) -> str | None:
    """Extract the spec ID from a filename, or None if not a spec file."""
    m = _SPEC_ID_RE.match(path.name)
    return m.group(1) if m else None


def _convert_changes(
    raw: set[tuple[Change, str]],
) -> list[SpecChangeEvent]:
    """Convert raw watchfiles events to domain events."""
    events: list[SpecChangeEvent] = []
    for change, path_str in raw:
        p = Path(path_str)
        events.append(
            SpecChangeEvent(
                change_type=_CHANGE_MAP[change],
                path=p,
                spec_id=_extract_spec_id(p),
            )
        )
    return events


# ---------------------------------------------------------------------------
# File filter
# ---------------------------------------------------------------------------


class SpecFileFilter(DefaultFilter):
    """Watchfiles filter that only passes spec ``.md`` files.

    Rejects:
    - Anything inside ``.cache/`` (avoids feedback loops with SQLite cache)
    - Non-``.md`` files
    - ``.tmp`` files
    - Everything rejected by ``DefaultFilter`` (``.git``, ``__pycache__``, etc.)
    """

    def __init__(self, specs_dir: Path) -> None:
        # Normalize to forward slashes for consistent prefix matching,
        # since watchfiles always delivers paths with OS-native separators
        # but we need to match on both platforms.
        cache_path = str(specs_dir / ".cache")
        self._cache_prefixes = {cache_path, cache_path.replace("\\", "/")}
        super().__init__()

    def __call__(self, change: Change, path: str) -> bool:
        if not super().__call__(change, path):
            return False
        if any(path.startswith(prefix) for prefix in self._cache_prefixes):
            return False
        if not path.endswith(".md"):
            return False
        if path.endswith(".tmp"):
            return False
        return True


# ---------------------------------------------------------------------------
# SpecWatcher
# ---------------------------------------------------------------------------


class SpecWatcher:
    """Background file watcher for the ``.specs/`` directory.

    Monitors spec files for changes and dispatches batched domain events
    to registered callbacks. Runs as a daemon thread using ``watchfiles``.

    Usage::

        watcher = SpecWatcher(specs_dir, callbacks=[my_callback])
        watcher.start()
        # ... later ...
        watcher.stop()

    Or as a context manager::

        with SpecWatcher(specs_dir, callbacks=[my_callback]) as w:
            # watcher is running
            ...
        # watcher is stopped
    """

    def __init__(
        self,
        specs_dir: Path,
        callbacks: list[WatcherCallback] | None = None,
        *,
        debounce: int = 500,
    ) -> None:
        self._specs_dir = Path(specs_dir)
        self._callbacks: list[WatcherCallback] = list(callbacks or [])
        self._debounce = debounce
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        """Whether the watcher thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def add_callback(self, callback: WatcherCallback) -> None:
        """Register an additional callback."""
        self._callbacks.append(callback)

    def start(self) -> None:
        """Start the watcher in a background daemon thread."""
        if self.is_running:
            logger.warning("watcher already running, ignoring start()")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            name="spec-watcher",
            daemon=True,
        )
        self._thread.start()
        logger.info("spec watcher started for {}", self._specs_dir)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the watcher to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("watcher thread did not exit within {}s", timeout)
            self._thread = None
        logger.info("spec watcher stopped")

    def __enter__(self) -> SpecWatcher:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    # --- Internal ----------------------------------------------------------

    def _watch_loop(self) -> None:
        """Main loop: iterate watchfiles and dispatch to callbacks."""
        file_filter = SpecFileFilter(self._specs_dir)

        try:
            for raw_changes in watch(
                self._specs_dir,
                watch_filter=file_filter,
                debounce=self._debounce,
                stop_event=self._stop_event,
                recursive=True,
            ):
                events = _convert_changes(raw_changes)
                if not events:
                    continue

                logger.debug(
                    "watcher detected {} change(s): {}",
                    len(events),
                    [(e.change_type, e.path.name) for e in events],
                )

                for callback in self._callbacks:
                    try:
                        callback(events)
                    except Exception:
                        logger.exception(
                            "watcher callback {} raised an exception",
                            getattr(callback, "__name__", repr(callback)),
                        )
        except Exception:
            if not self._stop_event.is_set():
                logger.exception("watcher loop crashed unexpectedly")


# ---------------------------------------------------------------------------
# Pre-built callbacks
# ---------------------------------------------------------------------------


def make_cache_callback(
    cache: SpecCache,
    parse_fn: Callable[[Path], Spec] = parse_spec_file,
    *,
    full_rebuild_threshold: int = 10,
    scan_fn: Callable[[], list[Path]] | None = None,
) -> WatcherCallback:
    """Create a watcher callback that keeps the SQLite cache in sync.

    For small batches, performs individual ``put``/``invalidate`` operations.
    When a batch exceeds *full_rebuild_threshold*, triggers a full
    ``cache.rebuild()`` instead — useful for bulk operations like
    ``git checkout`` that touch many files at once.

    Args:
        cache: The SpecCache instance to update.
        parse_fn: Function to parse a spec file (default: ``parse_spec_file``).
        full_rebuild_threshold: Number of changes that triggers a full rebuild.
        scan_fn: Optional function that returns all spec file paths for a
            full rebuild. If None, full rebuild re-parses only the files
            in the change batch (less complete but avoids needing a scan fn).
    """

    def _on_changes(events: list[SpecChangeEvent]) -> None:
        if len(events) >= full_rebuild_threshold and scan_fn is not None:
            logger.info(
                "batch of {} changes exceeds threshold ({}), triggering full rebuild",
                len(events),
                full_rebuild_threshold,
            )
            specs: list[Spec] = []
            for path in scan_fn():
                try:
                    specs.append(parse_fn(path))
                except (ParseError, OSError) as exc:
                    logger.warning("rebuild: skipping {}: {}", path.name, exc)
            cache.rebuild(specs)
            return

        for event in events:
            if event.change_type == "deleted":
                if event.spec_id:
                    cache.invalidate(event.spec_id)
                    logger.debug("cache: invalidated {}", event.spec_id)
            else:
                # added or modified
                try:
                    spec = parse_fn(event.path)
                    cache.put(spec)
                    logger.debug("cache: updated {}", event.spec_id or event.path.name)
                except (ParseError, OSError) as exc:
                    logger.warning(
                        "cache: failed to parse {}: {}", event.path.name, exc
                    )

    _on_changes.__name__ = "cache_callback"
    return _on_changes


def make_notify_callback(
    notify_fn: Callable[[list[SpecChangeEvent]], None],
) -> WatcherCallback:
    """Create a watcher callback that forwards events to a notification function.

    Intended to be wired to a WebSocket broadcast when the web layer
    is implemented (DIA-010). For now, this is a thin pass-through that
    establishes the callback pattern.

    Args:
        notify_fn: Function to call with the list of change events.
            Typically broadcasts to connected WebSocket clients.
    """
    return notify_fn


__all__ = [
    "SpecChangeEvent",
    "SpecFileFilter",
    "SpecWatcher",
    "WatcherCallback",
    "make_cache_callback",
    "make_notify_callback",
]
