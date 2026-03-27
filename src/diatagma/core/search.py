"""Full-text search over task files.

Provides keyword and field-scoped search across all task metadata and
body content. Backed by the SQLite FTS5 extension via the cache DB.

Key functions:
    search_tasks(query: str, fields: list[str] | None) → list[Task]
    find_related(task_id: str) → list[Task]
"""
