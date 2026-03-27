"""TaskStore — CRUD operations over the .tasks/ directory.

The single source-of-truth layer. Every read/write goes through the
filesystem. The store discovers task files by scanning configured
directories, delegates parsing to parser.py, and coordinates with
cache.py for acceleration.

Key class:
    TaskStore(tasks_dir: Path)
        .list(filters, sort_by)  → list[Task]
        .get(task_id)            → Task
        .create(prefix, title, template, **meta) → Task
        .update(task_id, **changes)
        .move_to_backlog(task_id)
        .move_to_archive(task_id)
        .next_id(prefix)         → str  (e.g. "DIA-004")
"""
