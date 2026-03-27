"""SQLite-backed read cache for parsed spec data.

Lives at .tasks/.cache/tasks.db (always gitignored). Accelerates
listing, filtering, and sorting without re-parsing every spec file.

Invalidation: mtime-based per file. On access, compare cached mtime vs
filesystem mtime. Full rebuild on startup or when cache version changes.

The cache is optional — if deleted, everything still works, just slower
on the first request.

Key class:
    SpecCache(cache_dir: Path)
        .get(spec_id)        → CachedSpec | None
        .put(spec)
        .invalidate(spec_id)
        .rebuild(specs: list[Spec])
        .query(filters, sort_by) → list[CachedSpec]
"""
