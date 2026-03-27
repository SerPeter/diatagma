"""SQLite-backed read cache for parsed task data.

Lives at .tasks/.cache/tasks.db (always gitignored). Accelerates
listing, filtering, and sorting without re-parsing every markdown file.

Invalidation: mtime-based per file. On access, compare cached mtime vs
filesystem mtime. Full rebuild on startup or when cache version changes.

The cache is optional — if deleted, everything still works, just slower
on the first request.

Key class:
    TaskCache(cache_dir: Path)
        .get(task_id)        → CachedTask | None
        .put(task)
        .invalidate(task_id)
        .rebuild(tasks: list[Task])
        .query(filters, sort_by) → list[CachedTask]
"""
