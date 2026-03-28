"""Tests for core.cache — SQLite cache creation, invalidation, queries."""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import pytest

from diatagma.core.cache import CACHE_VERSION, SpecCache
from diatagma.core.models import Spec, SpecMeta
from diatagma.core.parser import parse_spec_file
from diatagma.core.store import SortField, SpecFilter
from tests.conftest import seed_spec_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(
    tasks_dir: Path,
    spec_id: str = "DIA-001",
    title: str = "Test spec",
    spec_type: str = "feature",
    status: str = "pending",
    **extra_meta: object,
) -> Spec:
    """Seed a spec file on disk and return the parsed Spec."""
    seed_spec_file(tasks_dir, spec_id, title, spec_type, status, **extra_meta)
    # Find the file just written
    for p in tasks_dir.glob(f"{spec_id}-*"):
        return parse_spec_file(p)
    msg = f"seed_spec_file did not create a file for {spec_id}"
    raise RuntimeError(msg)


# ===========================================================================
# TestInit
# ===========================================================================


class TestInit:
    """Database creation and initialization."""

    def test_creates_db_file(self, tmp_tasks_dir: Path) -> None:
        cache_dir = tmp_tasks_dir / ".cache"
        cache = SpecCache(cache_dir)
        assert (cache_dir / "tasks.db").exists()
        cache.close()

    def test_creates_tables(self, spec_cache: SpecCache) -> None:
        tables = {
            row["name"]
            for row in spec_cache._conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }
        assert "tasks" in tables
        assert "cache_meta" in tables
        assert "tasks_fts" in tables

    def test_wal_mode_enabled(self, spec_cache: SpecCache) -> None:
        mode = spec_cache._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_version_stored(self, spec_cache: SpecCache) -> None:
        row = spec_cache._conn.execute(
            "SELECT value FROM cache_meta WHERE key = 'version'"
        ).fetchone()
        assert row is not None
        assert row["value"] == CACHE_VERSION


# ===========================================================================
# TestVersion
# ===========================================================================


class TestVersion:
    """Cache version checking and data clearing."""

    def test_version_mismatch_clears_data(self, tmp_tasks_dir: Path) -> None:
        cache_dir = tmp_tasks_dir / ".cache"
        cache = SpecCache(cache_dir)

        # Seed a spec into the cache
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Version test")
        cache.put(spec)
        assert cache.get("DIA-001") is not None

        # Tamper with version
        cache._conn.execute("UPDATE cache_meta SET value = 'old' WHERE key = 'version'")
        cache._conn.commit()
        cache.close()

        # Re-open — should detect mismatch and clear
        cache2 = SpecCache(cache_dir)
        assert cache2.get("DIA-001") is None
        count = cache2._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        assert count == 0
        cache2.close()

    def test_version_match_preserves_data(self, tmp_tasks_dir: Path) -> None:
        cache_dir = tmp_tasks_dir / ".cache"
        cache = SpecCache(cache_dir)
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Preserved")
        cache.put(spec)
        cache.close()

        cache2 = SpecCache(cache_dir)
        result = cache2.get("DIA-001")
        assert result is not None
        assert result.meta.title == "Preserved"
        cache2.close()


# ===========================================================================
# TestPutAndGet
# ===========================================================================


class TestPutAndGet:
    """put() and get() round-tripping."""

    def test_round_trip(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Round trip")
        spec_cache.put(spec)
        result = spec_cache.get("DIA-001")
        assert result is not None
        assert result.meta.id == "DIA-001"
        assert result.meta.title == "Round trip"
        assert result.file_path == spec.file_path

    def test_get_nonexistent(self, spec_cache: SpecCache) -> None:
        assert spec_cache.get("DIA-999") is None

    def test_get_stale_mtime(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Stale test")
        spec_cache.put(spec)

        # Touch the file to change mtime
        assert spec.file_path is not None
        time.sleep(0.05)
        spec.file_path.touch()

        assert spec_cache.get("DIA-001") is None

    def test_get_missing_file(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Will be deleted")
        spec_cache.put(spec)

        assert spec.file_path is not None
        spec.file_path.unlink()

        result = spec_cache.get("DIA-001")
        assert result is None

        # Should also clean up the row
        row = spec_cache._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE id = 'DIA-001'"
        ).fetchone()[0]
        assert row == 0

    def test_put_overwrites(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Original")
        spec_cache.put(spec)

        # Update the spec meta and re-put
        updated_meta = spec.meta.model_dump()
        updated_meta["title"] = "Updated"
        spec.meta = SpecMeta.model_validate(updated_meta)
        spec_cache.put(spec)

        result = spec_cache.get("DIA-001")
        assert result is not None
        assert result.meta.title == "Updated"

    def test_list_fields_roundtrip(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(
            tmp_tasks_dir,
            "DIA-001",
            "Lists",
            tags=["core", "models"],
            dependencies=["DIA-002"],
            blocked_by=["DIA-003"],
            related_to=["DIA-004"],
        )
        spec_cache.put(spec)
        result = spec_cache.get("DIA-001")
        assert result is not None
        assert result.meta.tags == ["core", "models"]
        assert result.meta.dependencies == ["DIA-002"]
        assert result.meta.blocked_by == ["DIA-003"]
        assert result.meta.related_to == ["DIA-004"]

    def test_date_fields_roundtrip(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(
            tmp_tasks_dir,
            "DIA-001",
            "Dates",
            due_date=date(2026, 6, 15),
        )
        # Set updated date
        meta_dict = spec.meta.model_dump()
        meta_dict["updated"] = date(2026, 3, 28)
        spec.meta = SpecMeta.model_validate(meta_dict)
        spec_cache.put(spec)

        result = spec_cache.get("DIA-001")
        assert result is not None
        assert result.meta.created == date(2026, 3, 27)
        assert result.meta.updated == date(2026, 3, 28)
        assert result.meta.due_date == date(2026, 6, 15)

    def test_nullable_fields(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Nullable")
        spec_cache.put(spec)
        result = spec_cache.get("DIA-001")
        assert result is not None
        assert result.meta.business_value is None
        assert result.meta.story_points is None
        assert result.meta.sprint is None
        assert result.meta.assignee is None
        assert result.meta.due_date is None
        assert result.meta.parent is None
        assert result.meta.updated is None


# ===========================================================================
# TestInvalidate
# ===========================================================================


class TestInvalidate:
    """invalidate() removes entries."""

    def test_invalidate_removes(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "To invalidate")
        spec_cache.put(spec)
        assert spec_cache.get("DIA-001") is not None

        spec_cache.invalidate("DIA-001")
        assert spec_cache.get("DIA-001") is None

    def test_invalidate_nonexistent(self, spec_cache: SpecCache) -> None:
        # Should not raise
        spec_cache.invalidate("DIA-999")

    def test_invalidate_clears_fts(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "FTS cleanup")
        spec_cache.put(spec)
        spec_cache.invalidate("DIA-001")

        fts_count = spec_cache._conn.execute(
            "SELECT COUNT(*) FROM tasks_fts WHERE id = 'DIA-001'"
        ).fetchone()[0]
        assert fts_count == 0


# ===========================================================================
# TestRebuild
# ===========================================================================


class TestRebuild:
    """rebuild() replaces all cached data."""

    def test_rebuild_replaces_all(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        # Put an old entry
        old_spec = _make_spec(tmp_tasks_dir, "DIA-001", "Old")
        spec_cache.put(old_spec)

        # Rebuild with different specs
        new1 = _make_spec(tmp_tasks_dir, "DIA-002", "New one")
        new2 = _make_spec(tmp_tasks_dir, "DIA-003", "New two")
        spec_cache.rebuild([new1, new2])

        assert spec_cache.get("DIA-001") is None
        assert spec_cache.get("DIA-002") is not None
        assert spec_cache.get("DIA-003") is not None

    def test_rebuild_empty_list(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Will be cleared")
        spec_cache.put(spec)

        spec_cache.rebuild([])

        count = spec_cache._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        assert count == 0


# ===========================================================================
# TestQuery
# ===========================================================================


class TestQuery:
    """query() with filters and sorting."""

    @pytest.fixture(autouse=True)
    def _seed_specs(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        """Seed 5 specs for query tests."""
        specs = [
            _make_spec(
                tmp_tasks_dir,
                "DIA-001",
                "Alpha feature",
                "feature",
                "pending",
                tags=["core"],
                business_value=500,
                story_points=5,
                parent="DIA-011",
                assignee="alice",
            ),
            _make_spec(
                tmp_tasks_dir,
                "DIA-002",
                "Beta bug",
                "bug",
                "in-progress",
                tags=["web"],
                business_value=300,
                story_points=3,
                assignee="bob",
            ),
            _make_spec(
                tmp_tasks_dir,
                "DIA-003",
                "Gamma chore",
                "chore",
                "done",
                tags=["core", "infra"],
                business_value=100,
                story_points=2,
            ),
            _make_spec(
                tmp_tasks_dir,
                "EX-001",
                "Delta spike",
                "spike",
                "pending",
                tags=["research"],
                business_value=200,
            ),
            _make_spec(
                tmp_tasks_dir,
                "DIA-004",
                "Epsilon docs",
                "docs",
                "pending",
                tags=["docs"],
                story_points=1,
            ),
        ]
        spec_cache.rebuild(specs)

    def test_query_no_filters(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query()
        assert len(results) == 5

    def test_filter_by_status_str(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(status="pending"))
        assert len(results) == 3
        assert all(s.meta.status == "pending" for s in results)

    def test_filter_by_status_list(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(status=["pending", "in-progress"]))
        assert len(results) == 4

    def test_filter_by_type_str(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(type="bug"))
        assert len(results) == 1
        assert results[0].meta.id == "DIA-002"

    def test_filter_by_type_list(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(type=["feature", "bug"]))
        assert len(results) == 2

    def test_filter_by_tags(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(tags=["core"]))
        ids = {s.meta.id for s in results}
        assert ids == {"DIA-001", "DIA-003"}

    def test_filter_by_tags_any_match(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(tags=["web", "research"]))
        ids = {s.meta.id for s in results}
        assert ids == {"DIA-002", "EX-001"}

    def test_filter_by_prefix(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(prefix="EX"))
        assert len(results) == 1
        assert results[0].meta.id == "EX-001"

    def test_filter_by_parent(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(parent="DIA-011"))
        assert len(results) == 1
        assert results[0].meta.id == "DIA-001"

    def test_filter_by_assignee(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(assignee="alice"))
        assert len(results) == 1
        assert results[0].meta.id == "DIA-001"

    def test_filter_by_search_title(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(search="Beta"))
        assert len(results) == 1
        assert results[0].meta.id == "DIA-002"

    def test_sort_by_id(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(sort_by=SortField.ID)
        ids = [s.meta.id for s in results]
        assert ids == ["DIA-001", "DIA-002", "DIA-003", "DIA-004", "EX-001"]

    def test_sort_by_title(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(sort_by=SortField.TITLE)
        titles = [s.meta.title for s in results]
        assert titles == sorted(titles, key=str.lower)

    def test_sort_by_created(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(sort_by=SortField.CREATED)
        # All have same created date in seed; just verify no error
        assert len(results) == 5

    def test_sort_by_business_value(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(sort_by=SortField.BUSINESS_VALUE, reverse=True)
        # Non-null values should come first, descending
        bvs = [s.meta.business_value for s in results]
        # First four have BV, last one (DIA-004) has None
        assert bvs[0] == 500
        assert bvs[1] == 300

    def test_sort_reverse(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(sort_by=SortField.ID, reverse=True)
        ids = [s.meta.id for s in results]
        assert ids == ["EX-001", "DIA-004", "DIA-003", "DIA-002", "DIA-001"]

    def test_query_excludes_stale(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        # Touch DIA-001's file to make it stale
        for p in tmp_tasks_dir.glob("DIA-001-*"):
            time.sleep(0.05)
            p.touch()

        results = spec_cache.query()
        ids = {s.meta.id for s in results}
        assert "DIA-001" not in ids
        assert len(results) == 4

    def test_combined_filters(self, spec_cache: SpecCache) -> None:
        results = spec_cache.query(SpecFilter(status="pending", prefix="DIA"))
        ids = {s.meta.id for s in results}
        assert ids == {"DIA-001", "DIA-004"}


# ===========================================================================
# TestFTS
# ===========================================================================


class TestFTS:
    """FTS5 full-text search."""

    def test_fts_search_title(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Pydantic models")
        spec_cache.put(spec)

        results = spec_cache.query(SpecFilter(search="Pydantic"))
        assert len(results) == 1
        assert results[0].meta.id == "DIA-001"

    def test_fts_search_body(self, spec_cache: SpecCache, tmp_tasks_dir: Path) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Cache module")
        # Set raw_body with searchable content
        spec.raw_body = "## Description\n\nImplement SQLite acceleration layer."
        spec_cache.put(spec)

        results = spec_cache.query(SpecFilter(search="acceleration"))
        assert len(results) == 1
        assert results[0].meta.id == "DIA-001"

    def test_fts_updated_on_put(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Original title")
        spec_cache.put(spec)

        # Update title and re-put
        meta_dict = spec.meta.model_dump()
        meta_dict["title"] = "New searchable title"
        spec.meta = SpecMeta.model_validate(meta_dict)
        spec_cache.put(spec)

        # Should find by new title
        results = spec_cache.query(SpecFilter(search="searchable"))
        assert len(results) == 1

        # Should NOT find by old title via FTS
        fts_rows = spec_cache._conn.execute(
            "SELECT * FROM tasks_fts WHERE tasks_fts MATCH ?",
            ('"Original title"',),
        ).fetchall()
        assert len(fts_rows) == 0

    def test_fts_cleared_on_invalidate(
        self, spec_cache: SpecCache, tmp_tasks_dir: Path
    ) -> None:
        spec = _make_spec(tmp_tasks_dir, "DIA-001", "Searchable spec")
        spec_cache.put(spec)
        spec_cache.invalidate("DIA-001")

        fts_count = spec_cache._conn.execute(
            "SELECT COUNT(*) FROM tasks_fts WHERE id = 'DIA-001'"
        ).fetchone()[0]
        assert fts_count == 0
