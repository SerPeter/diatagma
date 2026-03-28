"""Tests for core.store — SpecStore CRUD over filesystem."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest

from diatagma.core.models import PrefixDef
from diatagma.core.parser import parse_spec_file
from diatagma.core.store import (
    InvalidPrefixError,
    SortField,
    SpecFilter,
    SpecNotFoundError,
    SpecStore,
    _slugify,
)
from tests.conftest import seed_spec_file


# ===========================================================================
# Slugify
# ===========================================================================


class TestSlugify:
    def test_basic(self):
        assert _slugify("Implement TaskStore") == "implement-taskstore"

    def test_special_chars(self):
        assert _slugify("Fix bug #42 (urgent!)") == "fix-bug-42-urgent"

    def test_spaces_and_underscores(self):
        assert _slugify("some_thing with spaces") == "some-thing-with-spaces"

    def test_truncation(self):
        slug = _slugify(
            "a very long title that exceeds the maximum length limit", max_length=20
        )
        assert len(slug) <= 20
        assert not slug.endswith("-")

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_preserves_hyphens(self):
        assert _slugify("my-thing") == "my-thing"


# ===========================================================================
# next_id
# ===========================================================================


class TestNextId:
    def test_first_id_in_empty_dir(self, spec_store: SpecStore):
        assert spec_store.next_id("DIA") == "DIA-001"

    def test_increments_from_existing(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "First")
        seed_spec_file(tmp_tasks_dir, "DIA-002", "Second")
        assert spec_store.next_id("DIA") == "DIA-003"

    def test_handles_gaps(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "First")
        seed_spec_file(tmp_tasks_dir, "DIA-005", "Fifth")
        assert spec_store.next_id("DIA") == "DIA-006"

    def test_four_digit_ids(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-999", "Nine ninety nine")
        assert spec_store.next_id("DIA") == "DIA-1000"

    def test_invalid_prefix_raises(self, spec_store: SpecStore):
        with pytest.raises(InvalidPrefixError, match="NOPE"):
            spec_store.next_id("NOPE")

    def test_multiple_prefixes_independent(
        self, spec_store: SpecStore, tmp_tasks_dir: Path
    ):
        seed_spec_file(tmp_tasks_dir, "DIA-003", "Dia three")
        seed_spec_file(tmp_tasks_dir, "EX-001", "Ex one", spec_type="spike")
        assert spec_store.next_id("DIA") == "DIA-004"
        assert spec_store.next_id("EX") == "EX-002"

    def test_finds_in_backlog_and_archive(
        self, spec_store: SpecStore, tmp_tasks_dir: Path
    ):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Active")
        seed_spec_file(tmp_tasks_dir / "backlog", "DIA-005", "Backlogged")
        seed_spec_file(tmp_tasks_dir / "archive", "DIA-010", "Archived")
        assert spec_store.next_id("DIA") == "DIA-011"


# ===========================================================================
# create
# ===========================================================================


class TestCreate:
    def test_creates_valid_file(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        spec = spec_store.create("DIA", "My new story")
        assert spec.file_path is not None
        assert spec.file_path.exists()
        # Re-parse from disk
        reparsed = parse_spec_file(spec.file_path)
        assert reparsed.meta.id == spec.meta.id

    def test_correct_frontmatter(self, spec_store: SpecStore):
        spec = spec_store.create("DIA", "Test spec", spec_type="bug")
        assert spec.meta.id == "DIA-001"
        assert spec.meta.title == "Test spec"
        assert spec.meta.status == "pending"
        assert spec.meta.type == "bug"
        assert spec.meta.created == date.today()

    def test_template_body_present(self, spec_store: SpecStore):
        spec = spec_store.create("DIA", "With template")
        assert spec.raw_body is not None
        assert "## Description" in spec.raw_body

    def test_slug_in_filename(self, spec_store: SpecStore):
        spec = spec_store.create("DIA", "Implement CRUD operations")
        assert spec.file_path is not None
        assert "implement-crud-operations" in spec.file_path.name

    def test_type_extension_mapping(self, spec_store: SpecStore):
        epic = spec_store.create("DIA", "An epic", spec_type="epic", template="epic")
        assert epic.file_path is not None
        assert epic.file_path.name.endswith(".epic.md")

        spike = spec_store.create("EX", "A spike", spec_type="spike")
        assert spike.file_path is not None
        assert spike.file_path.name.endswith(".spike.md")

        feature = spec_store.create("DIA", "A feature", spec_type="feature")
        assert feature.file_path is not None
        assert feature.file_path.name.endswith(".story.md")

    def test_meta_overrides(self, spec_store: SpecStore):
        spec = spec_store.create(
            "DIA",
            "With overrides",
            business_value=300,
            tags=["backend"],
        )
        assert spec.meta.business_value == 300
        assert spec.meta.tags == ["backend"]

    def test_sequential_creates(self, spec_store: SpecStore):
        s1 = spec_store.create("DIA", "First")
        s2 = spec_store.create("DIA", "Second")
        s3 = spec_store.create("DIA", "Third")
        assert s1.meta.id == "DIA-001"
        assert s2.meta.id == "DIA-002"
        assert s3.meta.id == "DIA-003"

    def test_changelog_called(self, tmp_tasks_dir, sample_prefixes, sample_templates):
        mutations: list[dict] = []

        def on_mut(spec_id, action, **kwargs):
            mutations.append({"spec_id": spec_id, "action": action, **kwargs})

        store = SpecStore(
            tmp_tasks_dir, sample_prefixes, sample_templates, on_mutation=on_mut
        )
        store.create("DIA", "Logged spec", agent_id="test-agent")
        assert len(mutations) == 1
        assert mutations[0]["spec_id"] == "DIA-001"
        assert mutations[0]["action"] == "created"
        assert mutations[0]["agent_id"] == "test-agent"

    def test_invalid_prefix_raises(self, spec_store: SpecStore):
        with pytest.raises(InvalidPrefixError):
            spec_store.create("BAD", "Nope")

    def test_explicit_template_override(self, spec_store: SpecStore):
        spec = spec_store.create(
            "DIA", "Spike via DIA", spec_type="spike", template="spike"
        )
        assert spec.raw_body is not None
        assert "## Research Questions" in spec.raw_body


# ===========================================================================
# get
# ===========================================================================


class TestGet:
    def test_get_existing(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Test get")
        spec = spec_store.get("DIA-001")
        assert spec.meta.id == "DIA-001"
        assert spec.meta.title == "Test get"

    def test_get_from_backlog(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir / "backlog", "DIA-042", "In backlog")
        spec = spec_store.get("DIA-042")
        assert spec.meta.id == "DIA-042"

    def test_get_from_archive(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir / "archive", "DIA-099", "Archived")
        spec = spec_store.get("DIA-099")
        assert spec.meta.id == "DIA-099"

    def test_nonexistent_raises(self, spec_store: SpecStore):
        with pytest.raises(SpecNotFoundError, match="DIA-999"):
            spec_store.get("DIA-999")


# ===========================================================================
# list
# ===========================================================================


class TestList:
    @pytest.fixture(autouse=True)
    def _seed_specs(self, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Models", tags=["core", "models"])
        seed_spec_file(
            tmp_tasks_dir,
            "DIA-002",
            "Parser",
            status="in-progress",
            tags=["core"],
            assignee="alice",
        )
        seed_spec_file(
            tmp_tasks_dir,
            "DIA-003",
            "Store",
            tags=["core", "store"],
            business_value=500,
            parent="DIA-011",
        )
        seed_spec_file(
            tmp_tasks_dir,
            "DIA-011",
            "Core epic",
            spec_type="epic",
        )
        seed_spec_file(
            tmp_tasks_dir / "backlog",
            "DIA-050",
            "Backlogged item",
        )

    def test_list_all(self, spec_store: SpecStore):
        specs = spec_store.list()
        assert len(specs) == 5

    def test_filter_by_status(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(status="in-progress"))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-002"

    def test_filter_by_multiple_statuses(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(status=["pending", "in-progress"]))
        assert len(specs) == 5

    def test_filter_by_type(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(type="epic"))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-011"

    def test_filter_by_tags(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(tags=["store"]))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-003"

    def test_filter_by_tags_any_match(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(tags=["models", "store"]))
        ids = {s.meta.id for s in specs}
        assert "DIA-001" in ids
        assert "DIA-003" in ids

    def test_filter_by_prefix(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(prefix="DIA"))
        assert len(specs) == 5

    def test_filter_by_parent(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(parent="DIA-011"))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-003"

    def test_filter_by_assignee(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(assignee="alice"))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-002"

    def test_filter_by_search(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(search="store"))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-003"

    def test_search_case_insensitive(self, spec_store: SpecStore):
        specs = spec_store.list(SpecFilter(search="MODELS"))
        assert len(specs) == 1
        assert specs[0].meta.id == "DIA-001"

    def test_sort_by_id(self, spec_store: SpecStore):
        specs = spec_store.list(sort_by=SortField.ID)
        ids = [s.meta.id for s in specs]
        assert ids == ["DIA-001", "DIA-002", "DIA-003", "DIA-011", "DIA-050"]

    def test_sort_by_id_reverse(self, spec_store: SpecStore):
        specs = spec_store.list(sort_by=SortField.ID, reverse=True)
        ids = [s.meta.id for s in specs]
        assert ids == ["DIA-050", "DIA-011", "DIA-003", "DIA-002", "DIA-001"]

    def test_sort_by_title(self, spec_store: SpecStore):
        specs = spec_store.list(sort_by=SortField.TITLE)
        titles = [s.meta.title for s in specs]
        assert titles == sorted(titles, key=str.lower)

    def test_empty_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        store = SpecStore(
            empty_dir,
            prefixes={"T": PrefixDef(description="Test")},
            templates={},
        )
        assert store.list() == []

    def test_skips_non_spec_files(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        (tmp_tasks_dir / "ROADMAP.md").write_text("# Roadmap", encoding="utf-8")
        (tmp_tasks_dir / "changelog.md").write_text("# Changelog", encoding="utf-8")
        specs = spec_store.list()
        ids = {s.meta.id for s in specs}
        assert "ROADMAP" not in ids
        assert len(specs) == 5  # same as before


# ===========================================================================
# update
# ===========================================================================


class TestUpdate:
    def test_update_meta_field(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Updatable")
        spec = spec_store.update("DIA-001", status="in-progress")
        assert spec.meta.status == "in-progress"
        # Verify on disk
        reloaded = spec_store.get("DIA-001")
        assert reloaded.meta.status == "in-progress"

    def test_update_sets_updated_date(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Track date")
        spec = spec_store.update("DIA-001", status="done")
        assert spec.meta.updated == date.today()

    def test_update_preserves_body_on_meta_only(
        self, spec_store: SpecStore, tmp_tasks_dir: Path
    ):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Body preserved")
        original = spec_store.get("DIA-001")
        original_desc = original.body.description

        updated = spec_store.update("DIA-001", status="in-progress")
        assert updated.body.description == original_desc

    def test_update_body_field(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Body change")
        spec = spec_store.update("DIA-001", description="New description.")
        assert spec.body.description == "New description."
        # raw_body should be cleared
        assert spec.raw_body is None

        reloaded = spec_store.get("DIA-001")
        assert reloaded.body.description == "New description."

    def test_update_nonexistent_raises(self, spec_store: SpecStore):
        with pytest.raises(SpecNotFoundError):
            spec_store.update("DIA-999", status="done")

    def test_changelog_called_per_field(
        self, tmp_tasks_dir, sample_prefixes, sample_templates
    ):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Log test")

        mutations: list[dict] = []

        def on_mut(spec_id, action, **kwargs):
            mutations.append({"spec_id": spec_id, "action": action, **kwargs})

        store = SpecStore(
            tmp_tasks_dir, sample_prefixes, sample_templates, on_mutation=on_mut
        )
        store.update("DIA-001", status="done", assignee="bob", agent_id="test")

        # Should have logged both field changes
        field_mutations = [m for m in mutations if m.get("field")]
        assert len(field_mutations) >= 2
        fields_logged = {m["field"] for m in field_mutations}
        assert "status" in fields_logged
        assert "assignee" in fields_logged

    def test_update_multiple_meta_fields(
        self, spec_store: SpecStore, tmp_tasks_dir: Path
    ):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Multi update")
        spec = spec_store.update(
            "DIA-001", status="in-progress", assignee="alice", business_value=100
        )
        assert spec.meta.status == "in-progress"
        assert spec.meta.assignee == "alice"
        assert spec.meta.business_value == 100


# ===========================================================================
# move
# ===========================================================================


class TestMove:
    def test_move_to_backlog(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Move me")
        spec = spec_store.move_to_backlog("DIA-001")
        assert spec.file_path is not None
        assert "backlog" in str(spec.file_path)
        # Original gone
        assert not list(tmp_tasks_dir.glob("DIA-001-*.md"))
        # In backlog
        assert list((tmp_tasks_dir / "backlog").glob("DIA-001-*.md"))

    def test_move_to_archive(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Archive me")
        spec = spec_store.move_to_archive("DIA-001")
        assert spec.file_path is not None
        assert "archive" in str(spec.file_path)
        assert list((tmp_tasks_dir / "archive").glob("DIA-001-*.md"))

    def test_move_preserves_content(self, spec_store: SpecStore, tmp_tasks_dir: Path):
        seed_spec_file(
            tmp_tasks_dir,
            "DIA-001",
            "Preserved",
            status="in-progress",
            tags=["core"],
        )
        before = spec_store.get("DIA-001")
        after = spec_store.move_to_backlog("DIA-001")
        assert before.meta.id == after.meta.id
        assert before.meta.title == after.meta.title
        assert before.meta.status == after.meta.status
        assert before.meta.tags == after.meta.tags
        assert before.body == after.body

    def test_move_nonexistent_raises(self, spec_store: SpecStore):
        with pytest.raises(SpecNotFoundError):
            spec_store.move_to_backlog("DIA-999")

    def test_changelog_called(self, tmp_tasks_dir, sample_prefixes, sample_templates):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Log move")

        mutations: list[dict] = []

        def on_mut(spec_id, action, **kwargs):
            mutations.append({"spec_id": spec_id, "action": action, **kwargs})

        store = SpecStore(
            tmp_tasks_dir, sample_prefixes, sample_templates, on_mutation=on_mut
        )
        store.move_to_archive("DIA-001", agent_id="bot")
        assert len(mutations) == 1
        assert mutations[0]["action"] == "moved to archive"
        assert mutations[0]["agent_id"] == "bot"


# ===========================================================================
# Concurrency
# ===========================================================================


class TestConcurrency:
    def test_concurrent_creates(self, tmp_tasks_dir, sample_prefixes, sample_templates):
        store = SpecStore(tmp_tasks_dir, sample_prefixes, sample_templates)

        def create_spec(i: int):
            return store.create("DIA", f"Concurrent spec {i}")

        with ThreadPoolExecutor(max_workers=10) as pool:
            specs = list(pool.map(create_spec, range(10)))

        ids = [s.meta.id for s in specs]
        assert len(set(ids)) == 10  # All unique
        # All files exist
        for spec in specs:
            assert spec.file_path is not None
            assert spec.file_path.exists()

    def test_concurrent_updates(self, tmp_tasks_dir, sample_prefixes, sample_templates):
        seed_spec_file(tmp_tasks_dir, "DIA-001", "Concurrent target")
        store = SpecStore(tmp_tasks_dir, sample_prefixes, sample_templates)

        statuses = ["pending", "in-progress", "in-review", "done", "cancelled"]

        def update_status(status: str):
            return store.update("DIA-001", status=status)

        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(update_status, statuses))

        # All completed without error; final state is one of the statuses
        final = store.get("DIA-001")
        assert final.meta.status in statuses
        # No corruption — file is parseable
        assert final.meta.id == "DIA-001"


# ===========================================================================
# Integration: create → get → update → move round-trip
# ===========================================================================


class TestIntegration:
    def test_full_lifecycle(self, spec_store: SpecStore):
        # Create
        spec = spec_store.create("DIA", "Lifecycle test", spec_type="feature")
        assert spec.meta.id == "DIA-001"

        # Get
        fetched = spec_store.get("DIA-001")
        assert fetched.meta.title == "Lifecycle test"

        # Update
        updated = spec_store.update("DIA-001", status="in-progress", assignee="alice")
        assert updated.meta.status == "in-progress"

        # List with filter
        active = spec_store.list(SpecFilter(status="in-progress"))
        assert len(active) == 1

        # Move to archive
        archived = spec_store.move_to_archive("DIA-001")
        assert archived.meta.id == "DIA-001"

        # Still findable via get
        found = spec_store.get("DIA-001")
        assert found.meta.status == "in-progress"

        # List shows it (archive is scanned)
        all_specs = spec_store.list()
        assert len(all_specs) == 1
