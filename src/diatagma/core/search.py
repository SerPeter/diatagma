"""Full-text search over spec files.

Provides keyword and field-scoped search across all spec metadata and
body content. Backed by the SQLite FTS5 extension via the cache DB.

Key functions:
    search_specs(query: str, fields: list[str] | None) → list[Spec]
    find_related(spec_id: str) → list[Spec]
"""
