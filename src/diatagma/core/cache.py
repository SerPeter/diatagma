"""SQLite-backed read cache for parsed spec data.

Lives at .tasks/.cache/tasks.db (always gitignored). Accelerates
listing, filtering, and sorting without re-parsing every spec file.

Invalidation: mtime-based per file. On access, compare cached mtime vs
filesystem mtime. Full rebuild on startup or when cache version changes.

The cache is optional — if deleted, everything still works, just slower
on the first request.

Key class:
    SpecCache(cache_dir: Path)
        .get(spec_id)        → Spec | None
        .put(spec)
        .invalidate(spec_id)
        .rebuild(specs: list[Spec])
        .query(filters, sort_by) → list[Spec]
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import orjson
from loguru import logger

from diatagma.core.models import SortField, Spec, SpecBody, SpecFilter, SpecMeta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_VERSION = "1"
"""Bump to force a full cache rebuild on schema changes."""

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS cache_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    type            TEXT NOT NULL,
    tags            TEXT NOT NULL DEFAULT '[]',
    business_value  INTEGER,
    story_points    INTEGER,
    sprint          TEXT,
    assignee        TEXT,
    due_date        TEXT,
    dependencies    TEXT NOT NULL DEFAULT '[]',
    blocked_by      TEXT NOT NULL DEFAULT '[]',
    related_to      TEXT NOT NULL DEFAULT '[]',
    parent          TEXT,
    created         TEXT NOT NULL,
    updated         TEXT,
    file_path       TEXT NOT NULL,
    file_mtime      REAL NOT NULL,
    priority_score  REAL NOT NULL DEFAULT 0.0,
    raw_body        TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee);
"""

_FTS_SQL = """\
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    id, title, body
);
"""

# ---------------------------------------------------------------------------
# Serialization helpers (module-level)
# ---------------------------------------------------------------------------

_LIST_FIELDS = frozenset({"tags", "dependencies", "blocked_by", "related_to"})
_DATE_FIELDS = frozenset({"created", "updated", "due_date"})


def _serialize_value(key: str, value: object) -> object:
    """Convert a Python value to a SQLite-compatible value."""
    if key in _LIST_FIELDS:
        return orjson.dumps(value).decode() if value else "[]"
    if key in _DATE_FIELDS:
        return value.isoformat() if isinstance(value, date) else value
    if isinstance(value, Path):
        return str(value)
    return value


def _deserialize_date(value: str | None) -> date | None:
    """Convert an ISO-8601 string back to a date, or None."""
    if value is None:
        return None
    return date.fromisoformat(value)


def _deserialize_list(value: str) -> list[str]:
    """Convert a JSON string back to a list."""
    return orjson.loads(value)


# ---------------------------------------------------------------------------
# SpecCache
# ---------------------------------------------------------------------------


class SpecCache:
    """SQLite-backed read cache for parsed spec data."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._cache_dir / "tasks.db"
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        if not self._check_version():
            self._reset_data()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # --- Core CRUD ---------------------------------------------------------

    def get(self, spec_id: str) -> Spec | None:
        """Retrieve a cached spec by ID.

        Returns None if the spec is not cached, the file is missing,
        or the cached mtime doesn't match the current file mtime.
        """
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (spec_id,)
        ).fetchone()
        if row is None:
            return None

        if not self._is_fresh(row):
            return None

        return self._row_to_spec(row)

    def put(self, spec: Spec) -> None:
        """Insert or replace a spec in the cache."""
        row = self._spec_to_row(spec)
        columns = ", ".join(row.keys())
        placeholders = ", ".join("?" for _ in row)
        values = list(row.values())

        self._conn.execute(
            f"INSERT OR REPLACE INTO tasks ({columns}) VALUES ({placeholders})",  # noqa: S608
            values,
        )

        # Update FTS index
        spec_id = spec.meta.id
        self._conn.execute("DELETE FROM tasks_fts WHERE id = ?", (spec_id,))
        self._conn.execute(
            "INSERT INTO tasks_fts (id, title, body) VALUES (?, ?, ?)",
            (spec_id, spec.meta.title, spec.raw_body or ""),
        )
        self._conn.commit()

    def invalidate(self, spec_id: str) -> None:
        """Remove a spec from the cache."""
        self._conn.execute("DELETE FROM tasks_fts WHERE id = ?", (spec_id,))
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (spec_id,))
        self._conn.commit()

    def rebuild(self, specs: list[Spec]) -> None:
        """Full cache rebuild: delete all rows, re-insert all specs."""
        self._conn.execute("DELETE FROM tasks")
        self._conn.execute("DELETE FROM tasks_fts")
        for spec in specs:
            row = self._spec_to_row(spec)
            columns = ", ".join(row.keys())
            placeholders = ", ".join("?" for _ in row)
            self._conn.execute(
                f"INSERT INTO tasks ({columns}) VALUES ({placeholders})",  # noqa: S608
                list(row.values()),
            )
            self._conn.execute(
                "INSERT INTO tasks_fts (id, title, body) VALUES (?, ?, ?)",
                (spec.meta.id, spec.meta.title, spec.raw_body or ""),
            )
        self._conn.commit()

    # --- Query -------------------------------------------------------------

    def query(
        self,
        filters: SpecFilter | None = None,
        sort_by: SortField = SortField.ID,
        reverse: bool = False,
    ) -> list[Spec]:
        """Filter and sort specs via SQL. Stale entries excluded."""
        where_clause, params = self._build_where(filters)
        order_clause = self._build_order_by(sort_by, reverse)

        sql = f"SELECT * FROM tasks {where_clause} {order_clause}"  # noqa: S608
        rows = self._conn.execute(sql, params).fetchall()

        results: list[Spec] = []
        for row in rows:
            if self._is_fresh(row):
                results.append(self._row_to_spec(row))
        return results

    # --- Internal helpers --------------------------------------------------

    def _init_db(self) -> None:
        """Create tables and set pragmas."""
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.executescript(_FTS_SQL)

    def _check_version(self) -> bool:
        """Return True if cached version matches CACHE_VERSION."""
        row = self._conn.execute(
            "SELECT value FROM cache_meta WHERE key = 'version'"
        ).fetchone()
        if row is None:
            return False
        return row["value"] == CACHE_VERSION

    def _reset_data(self) -> None:
        """Clear all cached data and set current version."""
        self._conn.execute("DELETE FROM tasks")
        self._conn.execute("DELETE FROM tasks_fts")
        self._conn.execute(
            "INSERT OR REPLACE INTO cache_meta (key, value) VALUES ('version', ?)",
            (CACHE_VERSION,),
        )
        self._conn.commit()

    def _spec_to_row(self, spec: Spec) -> dict[str, object]:
        """Serialize a Spec to a dict of SQLite-compatible values."""
        meta_dict = spec.meta.model_dump()
        row: dict[str, object] = {}
        for key, value in meta_dict.items():
            row[key] = _serialize_value(key, value)

        assert spec.file_path is not None
        row["file_path"] = str(spec.file_path)
        row["file_mtime"] = spec.file_path.stat().st_mtime
        row["priority_score"] = spec.priority_score
        row["raw_body"] = spec.raw_body
        return row

    def _row_to_spec(self, row: sqlite3.Row) -> Spec:
        """Deserialize a SQLite row back to a Spec object."""
        meta_dict: dict[str, object] = {
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "type": row["type"],
            "tags": _deserialize_list(row["tags"]),
            "business_value": row["business_value"],
            "story_points": row["story_points"],
            "sprint": row["sprint"],
            "assignee": row["assignee"],
            "due_date": _deserialize_date(row["due_date"]),
            "dependencies": _deserialize_list(row["dependencies"]),
            "blocked_by": _deserialize_list(row["blocked_by"]),
            "related_to": _deserialize_list(row["related_to"]),
            "parent": row["parent"],
            "created": _deserialize_date(row["created"]),
            "updated": _deserialize_date(row["updated"]),
        }

        meta = SpecMeta.model_validate(meta_dict)
        return Spec(
            meta=meta,
            body=SpecBody(),
            file_path=Path(row["file_path"]),
            raw_body=row["raw_body"],
            priority_score=row["priority_score"],
        )

    def _is_fresh(self, row: sqlite3.Row) -> bool:
        """Check if cached mtime matches current filesystem mtime."""
        path = Path(row["file_path"])
        if not path.exists():
            # File gone — clean up the stale row
            spec_id = row["id"]
            self._conn.execute("DELETE FROM tasks_fts WHERE id = ?", (spec_id,))
            self._conn.execute("DELETE FROM tasks WHERE id = ?", (spec_id,))
            self._conn.commit()
            logger.debug("cache cleanup: file gone for {}", spec_id)
            return False

        return path.stat().st_mtime == row["file_mtime"]

    def _build_where(self, filters: SpecFilter | None) -> tuple[str, list[object]]:
        """Translate SpecFilter to SQL WHERE clause + params."""
        if filters is None:
            return "", []

        clauses: list[str] = []
        params: list[object] = []

        # status
        if filters.status is not None:
            if isinstance(filters.status, str):
                clauses.append("status = ?")
                params.append(filters.status)
            else:
                placeholders = ", ".join("?" for _ in filters.status)
                clauses.append(f"status IN ({placeholders})")
                params.extend(filters.status)

        # type
        if filters.type is not None:
            if isinstance(filters.type, str):
                clauses.append("type = ?")
                params.append(filters.type)
            else:
                placeholders = ", ".join("?" for _ in filters.type)
                clauses.append(f"type IN ({placeholders})")
                params.extend(filters.type)

        # tags (ANY match)
        if filters.tags is not None:
            placeholders = ", ".join("?" for _ in filters.tags)
            clauses.append(
                f"EXISTS (SELECT 1 FROM json_each(tasks.tags) WHERE value IN ({placeholders}))"
            )
            params.extend(filters.tags)

        # prefix
        if filters.prefix is not None:
            clauses.append("id LIKE ? || '-%'")
            params.append(filters.prefix)

        # parent
        if filters.parent is not None:
            clauses.append("parent = ?")
            params.append(filters.parent)

        # assignee
        if filters.assignee is not None:
            clauses.append("assignee = ?")
            params.append(filters.assignee)

        # search (FTS5 with LIKE fallback)
        if filters.search is not None:
            clauses.append(
                "("
                "id IN (SELECT id FROM tasks_fts WHERE tasks_fts MATCH ?) "
                "OR title LIKE '%' || ? || '%' COLLATE NOCASE"
                ")"
            )
            # FTS5 match term — quote for safety
            params.append(f'"{filters.search}"')
            params.append(filters.search)

        if not clauses:
            return "", []

        return "WHERE " + " AND ".join(clauses), params

    def _build_order_by(self, sort_by: SortField, reverse: bool) -> str:
        """Translate SortField to SQL ORDER BY clause."""
        direction = "DESC" if reverse else "ASC"

        match sort_by:
            case SortField.ID:
                expr = (
                    f"substr(id, 1, instr(id, '-') - 1) {direction}, "
                    f"CAST(substr(id, instr(id, '-') + 1) AS INTEGER) {direction}"
                )
                return f"ORDER BY {expr}"
            case SortField.TITLE:
                return f"ORDER BY title COLLATE NOCASE {direction}"
            case SortField.STATUS:
                return f"ORDER BY status {direction}"
            case SortField.CREATED:
                return f"ORDER BY created {direction}"
            case SortField.UPDATED:
                return f"ORDER BY COALESCE(updated, '0001-01-01') {direction}"
            case SortField.BUSINESS_VALUE:
                return f"ORDER BY COALESCE(business_value, -9999) {direction}"
            case SortField.STORY_POINTS:
                return f"ORDER BY COALESCE(story_points, 0) {direction}"
            case SortField.PRIORITY:
                return f"ORDER BY priority_score {direction}"
            case _:
                return f"ORDER BY id {direction}"


__all__ = [
    "CACHE_VERSION",
    "SpecCache",
]
