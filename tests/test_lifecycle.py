"""Tests for lifecycle automation — completion metadata, auto-complete, guards, archival."""

from datetime import date
from pathlib import Path

import pytest

from diatagma.core.graph import SpecGraph
from diatagma.core.lifecycle import LifecycleEngine, LifecycleError
from diatagma.core.models import (
    PrefixDef,
    Settings,
    Spec,
    SpecBody,
    SpecLinks,
    SpecMeta,
)
from diatagma.core.store import SpecStore
from tests.conftest import seed_spec_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(
    spec_id: str,
    title: str = "Test",
    status: str = "pending",
    spec_type: str = "feature",
    parent: str | None = None,
    cycle: str | None = None,
    blocked_by: list[str] | None = None,
) -> Spec:
    """Build an in-memory Spec for graph/list operations."""
    links = SpecLinks(blocked_by=blocked_by or [])
    return Spec(
        meta=SpecMeta(
            id=spec_id,
            title=title,
            status=status,
            type=spec_type,
            parent=parent,
            cycle=cycle,
            links=links,
            created=date(2026, 3, 27),
        ),
        body=SpecBody(description=f"Description for {spec_id}."),
    )


def _build_graph(specs: list[Spec]) -> SpecGraph:
    """Build a SpecGraph from specs."""
    graph = SpecGraph()
    graph.build(specs)
    return graph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prefixes() -> dict[str, PrefixDef]:
    return {"DIA": PrefixDef(description="test", template="story")}


@pytest.fixture
def store(tmp_specs_dir: Path, prefixes) -> SpecStore:
    return SpecStore(tmp_specs_dir, prefixes, templates={"story": "", "epic": ""})


@pytest.fixture
def engine(store: SpecStore) -> LifecycleEngine:
    return LifecycleEngine(store=store, settings=Settings(auto_complete_parent=True))


# ===========================================================================
# TestCompletionContext
# ===========================================================================


class TestCompletionContext:
    """update_status() returns rich CompletionContext on done transition."""

    def test_parent_progress(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-011", "Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir, "DIA-001", "Child 1", status="done", parent="DIA-011"
        )
        seed_spec_file(
            tmp_specs_dir, "DIA-002", "Child 2", status="done", parent="DIA-011"
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-003",
            "Child 3",
            status="in-progress",
            parent="DIA-011",
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-003", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert result.completion.parent_progress == "3/3 stories in DIA-011 done"

    def test_newly_unblocked(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Blocker", status="in-progress")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Blocked",
            status="pending",
            links=SpecLinks(blocked_by=["DIA-001"]),
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-001", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert "DIA-002" in result.completion.newly_unblocked

    def test_next_ready_capped(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        # Create 7 ready specs + 1 blocker
        seed_spec_file(tmp_specs_dir, "DIA-001", "Blocker", status="in-progress")
        for i in range(2, 9):
            seed_spec_file(
                tmp_specs_dir,
                f"DIA-{i:03d}",
                f"Ready {i}",
                status="pending",
            )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-001", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert len(result.completion.next_ready) <= 5

    def test_cycle_progress(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Done", status="done", cycle="Cycle 1")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Working",
            status="in-progress",
            cycle="Cycle 1",
        )
        seed_spec_file(
            tmp_specs_dir, "DIA-003", "Pending", status="pending", cycle="Cycle 1"
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-002", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert result.completion.cycle_progress == "2/3 specs in Cycle 1 done"
        assert result.completion.cycle_complete is False

    def test_cycle_complete(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Done", status="done", cycle="Cycle 1")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Last one",
            status="in-progress",
            cycle="Cycle 1",
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-002", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert result.completion.cycle_complete is True

    def test_non_done_status_no_completion(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Pending", status="pending")

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-001", "in-progress", graph=graph, all_specs=all_specs
        )
        assert result.completion is None


# ===========================================================================
# TestAutoCompleteParent
# ===========================================================================


class TestAutoCompleteParent:
    """Parent epics auto-complete when all children are terminal."""

    def test_last_child_done_completes_parent(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-011", "Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir, "DIA-001", "Child 1", status="done", parent="DIA-011"
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Child 2",
            status="in-progress",
            parent="DIA-011",
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-002", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert "DIA-011" in result.completion.auto_completed_parents

        # Verify parent is actually done on disk
        parent = store.get("DIA-011")
        assert parent.meta.status == "done"

    def test_recursive_auto_complete(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-100", "Grand epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-011",
            "Child epic",
            spec_type="epic",
            parent="DIA-100",
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Last story",
            status="in-progress",
            parent="DIA-011",
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-001", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert "DIA-011" in result.completion.auto_completed_parents
        assert "DIA-100" in result.completion.auto_completed_parents

    def test_cancelled_counts_as_terminal(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-011", "Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Cancelled",
            status="cancelled",
            parent="DIA-011",
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Last one",
            status="in-progress",
            parent="DIA-011",
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-002", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert "DIA-011" in result.completion.auto_completed_parents

    def test_setting_disabled_skips(self, store: SpecStore, tmp_specs_dir: Path):
        engine = LifecycleEngine(
            store=store, settings=Settings(auto_complete_parent=False)
        )
        seed_spec_file(tmp_specs_dir, "DIA-011", "Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Last child",
            status="in-progress",
            parent="DIA-011",
        )

        all_specs = store.list()
        graph = _build_graph(all_specs)

        result = engine.update_status(
            "DIA-001", "done", graph=graph, all_specs=all_specs
        )
        assert result.completion is not None
        assert result.completion.auto_completed_parents == []

        parent = store.get("DIA-011")
        assert parent.meta.status == "pending"

    def test_changelog_records_auto_complete(self, tmp_specs_dir: Path, prefixes):
        mutations: list[tuple] = []

        def on_mutation(spec_id, action, **kwargs):
            mutations.append((spec_id, action, kwargs))

        s = SpecStore(
            tmp_specs_dir,
            prefixes,
            templates={"story": "", "epic": ""},
            on_mutation=on_mutation,
        )
        engine = LifecycleEngine(store=s, settings=Settings(auto_complete_parent=True))

        seed_spec_file(tmp_specs_dir, "DIA-011", "Epic", spec_type="epic")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Last one",
            status="in-progress",
            parent="DIA-011",
        )

        all_specs = s.list()
        graph = _build_graph(all_specs)
        engine.update_status("DIA-001", "done", graph=graph, all_specs=all_specs)

        # Find the parent status change in mutations
        parent_mutations = [
            (sid, act, kw) for sid, act, kw in mutations if sid == "DIA-011"
        ]
        assert len(parent_mutations) > 0
        assert any(kw.get("new") == "done" for _, _, kw in parent_mutations)


# ===========================================================================
# TestReopeningGuards
# ===========================================================================


class TestReopeningGuards:
    """Lifecycle guards on create_spec protect completed epics and cycles."""

    def test_child_to_done_epic_reopens(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir, "DIA-011", "Done epic", spec_type="epic", status="done"
        )

        engine.create_spec("DIA", "New child", parent="DIA-011")

        epic = store.get("DIA-011")
        assert epic.meta.status == "in-progress"

    def test_child_to_archived_epic_errors(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir, "DIA-011", "Epic to archive", spec_type="epic", status="done"
        )
        store.move_to_archive("DIA-011")

        with pytest.raises(LifecycleError, match="archived"):
            engine.create_spec("DIA", "New child", parent="DIA-011")

    def test_child_to_archived_epic_with_reopen(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir, "DIA-011", "Epic to archive", spec_type="epic", status="done"
        )
        store.move_to_archive("DIA-011")

        engine.create_spec("DIA", "New child", reopen=True, parent="DIA-011")

        epic = store.get("DIA-011")
        assert epic.meta.status == "in-progress"
        assert not store.is_archived("DIA-011")

    def test_spec_to_completed_cycle_errors(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Done", status="done", cycle="Cycle 1")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Also done",
            status="done",
            cycle="Cycle 1",
        )

        all_specs = store.list()

        with pytest.raises(LifecycleError, match="complete"):
            engine.create_spec("DIA", "New task", all_specs=all_specs, cycle="Cycle 1")

    def test_spec_to_completed_cycle_with_reopen(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Done", status="done", cycle="Cycle 1")

        all_specs = store.list()

        # Should not raise
        spec = engine.create_spec(
            "DIA",
            "New task",
            reopen=True,
            all_specs=all_specs,
            cycle="Cycle 1",
        )
        assert spec.meta.id is not None


# ===========================================================================
# TestBatchArchival
# ===========================================================================


class TestBatchArchival:
    """archive_cycle and archive_done move terminal specs to archive."""

    def test_archive_cycle_terminal_only(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Done", status="done", cycle="Cycle 1")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Cancelled",
            status="cancelled",
            cycle="Cycle 1",
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-003",
            "Active",
            status="in-progress",
            cycle="Cycle 1",
        )

        result = engine.archive_cycle("Cycle 1")

        assert sorted(result.archived) == ["DIA-001", "DIA-002"]
        assert result.skipped == ["DIA-003"]
        assert len(result.warnings) == 1

    def test_archive_cycle_warns_remaining(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Active",
            status="in-progress",
            cycle="Cycle 1",
        )

        result = engine.archive_cycle("Cycle 1")

        assert result.archived == []
        assert result.skipped == ["DIA-001"]
        assert len(result.warnings) == 1
        assert "in-progress" in result.warnings[0]

    def test_archive_done_all_terminal(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir, "DIA-001", "Done 1", status="done", cycle="Cycle 1"
        )
        seed_spec_file(
            tmp_specs_dir, "DIA-002", "Done 2", status="done", cycle="Cycle 2"
        )
        seed_spec_file(tmp_specs_dir, "DIA-003", "Active", status="in-progress")

        result = engine.archive_done()

        assert sorted(result.archived) == ["DIA-001", "DIA-002"]
        # archive_done pre-filters to terminal, so no skipped
        assert result.skipped == []

    def test_archive_done_noop_when_nothing_terminal(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Active", status="in-progress")

        result = engine.archive_done()

        assert result.archived == []
        assert result.skipped == []


# ===========================================================================
# TestConsistencyValidation
# ===========================================================================


class TestConsistencyValidation:
    """validate_consistency detects and handles lifecycle invariant violations."""

    def test_done_epic_with_active_children(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir, "DIA-011", "Done epic", spec_type="epic", status="done"
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Active child",
            status="pending",
            parent="DIA-011",
        )

        all_specs = store.list()
        issues = engine.validate_consistency(all_specs=all_specs)

        epic_issues = [i for i in issues if i.spec_id == "DIA-011"]
        assert len(epic_issues) == 1
        assert epic_issues[0].type == "epic_done_with_active_children"
        assert epic_issues[0].auto_corrected is True

        # Verify auto-correction
        epic = store.get("DIA-011")
        assert epic.meta.status == "in-progress"

    def test_cycle_with_mixed_status_warns(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Done", status="done", cycle="Cycle 1")
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Active",
            status="pending",
            cycle="Cycle 1",
        )

        all_specs = store.list()
        issues = engine.validate_consistency(all_specs=all_specs)

        cycle_issues = [i for i in issues if i.type == "cycle_complete_with_active"]
        assert len(cycle_issues) == 1
        assert cycle_issues[0].auto_corrected is False

    def test_orphaned_children(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Orphan",
            parent="DIA-999",
        )

        all_specs = store.list()
        issues = engine.validate_consistency(all_specs=all_specs)

        orphan_issues = [i for i in issues if i.type == "orphaned_child"]
        assert len(orphan_issues) == 1
        assert orphan_issues[0].spec_id == "DIA-001"
        assert "DIA-999" in orphan_issues[0].message

    def test_returns_structured_issues(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(
            tmp_specs_dir, "DIA-011", "Done epic", spec_type="epic", status="done"
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-001",
            "Active child",
            status="pending",
            parent="DIA-011",
        )
        seed_spec_file(
            tmp_specs_dir,
            "DIA-002",
            "Orphan",
            parent="DIA-999",
        )

        all_specs = store.list()
        issues = engine.validate_consistency(all_specs=all_specs)

        assert len(issues) >= 2
        for issue in issues:
            assert issue.type
            assert issue.spec_id
            assert issue.message

    def test_clean_state_no_issues(
        self, engine: LifecycleEngine, store: SpecStore, tmp_specs_dir: Path
    ):
        seed_spec_file(tmp_specs_dir, "DIA-001", "Normal", status="pending")
        seed_spec_file(tmp_specs_dir, "DIA-002", "Also normal", status="in-progress")

        all_specs = store.list()
        issues = engine.validate_consistency(all_specs=all_specs)

        assert issues == []
