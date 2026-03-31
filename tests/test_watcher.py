"""Tests for core.watcher — file watcher and callbacks."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

from watchfiles import Change

from diatagma.core.watcher import (
    SpecChangeEvent,
    SpecFileFilter,
    SpecWatcher,
    _convert_changes,
    _extract_spec_id,
    make_cache_callback,
)


# ===========================================================================
# TestExtractSpecId
# ===========================================================================


class TestExtractSpecId:
    """Spec ID extraction from filenames."""

    def test_standard_story(self):
        assert _extract_spec_id(Path("DIA-001-my-story.story.md")) == "DIA-001"

    def test_standard_epic(self):
        assert _extract_spec_id(Path("DIA-011-core-epic.epic.md")) == "DIA-011"

    def test_standard_spike(self):
        assert _extract_spec_id(Path("DIA-050-research.spike.md")) == "DIA-050"

    def test_long_prefix(self):
        assert _extract_spec_id(Path("ABCDE-999-something.story.md")) == "ABCDE-999"

    def test_large_number(self):
        assert _extract_spec_id(Path("DIA-12345-big.story.md")) == "DIA-12345"

    def test_multiple_hyphens_in_slug(self):
        assert _extract_spec_id(Path("DIA-003-my-long-slug-name.story.md")) == "DIA-003"

    def test_non_spec_md(self):
        assert _extract_spec_id(Path("README.md")) is None

    def test_non_spec_changelog(self):
        assert _extract_spec_id(Path("changelog.md")) is None

    def test_no_extension(self):
        assert _extract_spec_id(Path("DIA-001-no-ext")) is None

    def test_lowercase_prefix(self):
        assert _extract_spec_id(Path("dia-001-lower.story.md")) is None


# ===========================================================================
# TestConvertChanges
# ===========================================================================


class TestConvertChanges:
    """Raw watchfiles events → domain events."""

    def test_added(self):
        raw = {(Change.added, "/tasks/DIA-001-foo.story.md")}
        events = _convert_changes(raw)
        assert len(events) == 1
        assert events[0].change_type == "added"
        assert events[0].spec_id == "DIA-001"

    def test_modified(self):
        raw = {(Change.modified, "/tasks/DIA-002-bar.story.md")}
        events = _convert_changes(raw)
        assert events[0].change_type == "modified"

    def test_deleted(self):
        raw = {(Change.deleted, "/tasks/DIA-003-baz.story.md")}
        events = _convert_changes(raw)
        assert events[0].change_type == "deleted"
        assert events[0].spec_id == "DIA-003"

    def test_non_spec_file(self):
        raw = {(Change.modified, "/tasks/README.md")}
        events = _convert_changes(raw)
        assert events[0].spec_id is None

    def test_batch(self):
        raw = {
            (Change.added, "/tasks/DIA-001-a.story.md"),
            (Change.modified, "/tasks/DIA-002-b.story.md"),
            (Change.deleted, "/tasks/DIA-003-c.story.md"),
        }
        events = _convert_changes(raw)
        assert len(events) == 3
        types = {e.change_type for e in events}
        assert types == {"added", "modified", "deleted"}


# ===========================================================================
# TestSpecFileFilter
# ===========================================================================


class TestSpecFileFilter:
    """Watchfiles filter for spec .md files."""

    def setup_method(self):
        self.specs_dir = Path("/project/.specs")
        self.f = SpecFileFilter(self.specs_dir)

    def test_md_file_passes(self):
        assert self.f(Change.modified, "/project/.specs/DIA-001-foo.story.md") is True

    def test_non_md_rejected(self):
        assert self.f(Change.modified, "/project/.specs/something.py") is False

    def test_txt_rejected(self):
        assert self.f(Change.modified, "/project/.specs/notes.txt") is False

    def test_cache_dir_rejected(self):
        assert self.f(Change.modified, "/project/.specs/.cache/tasks.db") is False

    def test_cache_subpath_rejected(self):
        assert (
            self.f(Change.modified, "/project/.specs/.cache/some/nested/file.md")
            is False
        )

    def test_tmp_file_rejected(self):
        assert self.f(Change.modified, "/project/.specs/edit.tmp") is False

    def test_backlog_md_passes(self):
        assert (
            self.f(Change.modified, "/project/.specs/backlog/DIA-010-foo.story.md")
            is True
        )

    def test_archive_md_passes(self):
        assert (
            self.f(Change.modified, "/project/.specs/archive/DIA-005-bar.story.md")
            is True
        )


# ===========================================================================
# TestSpecWatcher
# ===========================================================================


class TestSpecWatcher:
    """Watcher lifecycle and event dispatch."""

    def test_start_stop_lifecycle(self, tmp_path: Path):
        watcher = SpecWatcher(tmp_path, debounce=100)
        watcher.start()
        assert watcher.is_running
        watcher.stop()
        assert not watcher.is_running

    def test_context_manager(self, tmp_path: Path):
        with SpecWatcher(tmp_path, debounce=100) as w:
            assert w.is_running
        assert not w.is_running

    def test_double_start_ignored(self, tmp_path: Path):
        watcher = SpecWatcher(tmp_path, debounce=100)
        watcher.start()
        watcher.start()  # should not raise or create second thread
        assert watcher.is_running
        watcher.stop()

    def test_stop_without_start(self, tmp_path: Path):
        watcher = SpecWatcher(tmp_path, debounce=100)
        watcher.stop()  # should not raise

    def test_file_creation_triggers_callback(self, tmp_path: Path):
        received = threading.Event()
        events_list: list[list[SpecChangeEvent]] = []

        def on_change(events: list[SpecChangeEvent]):
            events_list.append(events)
            received.set()

        with SpecWatcher(tmp_path, callbacks=[on_change], debounce=100):
            # Create a spec file
            spec_file = tmp_path / "DIA-001-test.story.md"
            spec_file.write_text("---\nid: DIA-001\n---\n")

            assert received.wait(timeout=5), "callback not invoked within 5s"

        assert len(events_list) >= 1
        all_events = [e for batch in events_list for e in batch]
        added = [e for e in all_events if e.change_type == "added"]
        assert len(added) >= 1
        assert added[0].spec_id == "DIA-001"

    def test_file_modification_triggers_callback(self, tmp_path: Path):
        # Create file before starting watcher
        spec_file = tmp_path / "DIA-002-test.story.md"
        spec_file.write_text("---\nid: DIA-002\n---\n")

        received = threading.Event()
        events_list: list[list[SpecChangeEvent]] = []

        def on_change(events: list[SpecChangeEvent]):
            events_list.append(events)
            received.set()

        with SpecWatcher(tmp_path, callbacks=[on_change], debounce=100):
            # Small delay to let watcher establish baseline
            time.sleep(0.3)

            # Modify the file
            spec_file.write_text("---\nid: DIA-002\ntitle: updated\n---\n")

            assert received.wait(timeout=5), "callback not invoked within 5s"

        all_events = [e for batch in events_list for e in batch]
        modified = [e for e in all_events if e.change_type == "modified"]
        assert len(modified) >= 1

    def test_file_deletion_triggers_callback(self, tmp_path: Path):
        spec_file = tmp_path / "DIA-003-test.story.md"
        spec_file.write_text("---\nid: DIA-003\n---\n")

        received = threading.Event()
        events_list: list[list[SpecChangeEvent]] = []

        def on_change(events: list[SpecChangeEvent]):
            events_list.append(events)
            received.set()

        with SpecWatcher(tmp_path, callbacks=[on_change], debounce=100):
            time.sleep(0.3)
            spec_file.unlink()

            assert received.wait(timeout=5), "callback not invoked within 5s"

        all_events = [e for batch in events_list for e in batch]
        deleted = [e for e in all_events if e.change_type == "deleted"]
        assert len(deleted) >= 1
        assert deleted[0].spec_id == "DIA-003"

    def test_multiple_callbacks_all_invoked(self, tmp_path: Path):
        received_1 = threading.Event()
        received_2 = threading.Event()

        def cb1(events: list[SpecChangeEvent]):
            received_1.set()

        def cb2(events: list[SpecChangeEvent]):
            received_2.set()

        with SpecWatcher(tmp_path, callbacks=[cb1, cb2], debounce=100):
            (tmp_path / "DIA-001-test.story.md").write_text("test")
            assert received_1.wait(timeout=5)
            assert received_2.wait(timeout=5)

    def test_callback_exception_doesnt_crash_watcher(self, tmp_path: Path):
        received = threading.Event()

        def bad_callback(events: list[SpecChangeEvent]):
            raise RuntimeError("callback exploded")

        def good_callback(events: list[SpecChangeEvent]):
            received.set()

        with SpecWatcher(
            tmp_path, callbacks=[bad_callback, good_callback], debounce=100
        ) as w:
            (tmp_path / "DIA-001-test.story.md").write_text("test")
            assert received.wait(timeout=5), "good callback should still fire"
            assert w.is_running, "watcher should still be running"

    def test_non_md_files_ignored(self, tmp_path: Path):
        received = threading.Event()
        events_list: list[list[SpecChangeEvent]] = []

        def on_change(events: list[SpecChangeEvent]):
            events_list.append(events)
            received.set()

        with SpecWatcher(tmp_path, callbacks=[on_change], debounce=100):
            # Create a non-md file — should be ignored
            (tmp_path / "notes.txt").write_text("hello")
            time.sleep(1)

            # Now create an md file — should trigger
            (tmp_path / "DIA-001-test.story.md").write_text("test")
            assert received.wait(timeout=5)

        # Only the .md file should be in events
        all_events = [e for batch in events_list for e in batch]
        paths = {e.path.name for e in all_events}
        assert "notes.txt" not in paths

    def test_add_callback_after_construction(self, tmp_path: Path):
        received = threading.Event()

        def late_callback(events: list[SpecChangeEvent]):
            received.set()

        watcher = SpecWatcher(tmp_path, debounce=100)
        watcher.add_callback(late_callback)

        with watcher:
            (tmp_path / "DIA-001-test.story.md").write_text("test")
            assert received.wait(timeout=5)


# ===========================================================================
# TestCacheCallback
# ===========================================================================


class TestCacheCallback:
    """Pre-built cache invalidation callback."""

    def test_modified_file_puts_to_cache(self, tmp_path: Path):
        cache = MagicMock()
        spec = MagicMock()
        parse_fn = MagicMock(return_value=spec)

        callback = make_cache_callback(cache, parse_fn=parse_fn)
        events = [
            SpecChangeEvent("modified", tmp_path / "DIA-001-foo.story.md", "DIA-001")
        ]
        callback(events)

        parse_fn.assert_called_once_with(tmp_path / "DIA-001-foo.story.md")
        cache.put.assert_called_once_with(spec)

    def test_added_file_puts_to_cache(self, tmp_path: Path):
        cache = MagicMock()
        spec = MagicMock()
        parse_fn = MagicMock(return_value=spec)

        callback = make_cache_callback(cache, parse_fn=parse_fn)
        events = [
            SpecChangeEvent("added", tmp_path / "DIA-002-bar.story.md", "DIA-002")
        ]
        callback(events)

        cache.put.assert_called_once_with(spec)

    def test_deleted_file_invalidates_cache(self):
        cache = MagicMock()
        callback = make_cache_callback(cache)
        events = [
            SpecChangeEvent("deleted", Path("/tasks/DIA-003-baz.story.md"), "DIA-003")
        ]
        callback(events)

        cache.invalidate.assert_called_once_with("DIA-003")

    def test_deleted_without_spec_id_skipped(self):
        cache = MagicMock()
        callback = make_cache_callback(cache)
        events = [SpecChangeEvent("deleted", Path("/tasks/README.md"), None)]
        callback(events)

        cache.invalidate.assert_not_called()

    def test_parse_error_skipped(self, tmp_path: Path):
        from diatagma.core.parser import ParseError

        cache = MagicMock()
        parse_fn = MagicMock(side_effect=ParseError("bad.md", "bad file"))

        callback = make_cache_callback(cache, parse_fn=parse_fn)
        events = [
            SpecChangeEvent("modified", tmp_path / "DIA-001-bad.story.md", "DIA-001")
        ]
        callback(events)

        cache.put.assert_not_called()

    def test_full_rebuild_above_threshold(self):
        cache = MagicMock()
        spec1 = MagicMock()
        spec2 = MagicMock()
        parse_fn = MagicMock(side_effect=[spec1, spec2])

        scan_fn = MagicMock(
            return_value=[Path("/a/DIA-001.story.md"), Path("/a/DIA-002.story.md")]
        )

        callback = make_cache_callback(
            cache,
            parse_fn=parse_fn,
            full_rebuild_threshold=3,
            scan_fn=scan_fn,
        )

        # 3 events >= threshold of 3
        events = [
            SpecChangeEvent(
                "modified", Path(f"/tasks/DIA-{i:03d}-x.story.md"), f"DIA-{i:03d}"
            )
            for i in range(1, 4)
        ]
        callback(events)

        scan_fn.assert_called_once()
        cache.rebuild.assert_called_once_with([spec1, spec2])
        # Should NOT have called individual put/invalidate
        cache.put.assert_not_called()
        cache.invalidate.assert_not_called()

    def test_no_full_rebuild_without_scan_fn(self):
        cache = MagicMock()
        spec = MagicMock()
        parse_fn = MagicMock(return_value=spec)

        callback = make_cache_callback(
            cache,
            parse_fn=parse_fn,
            full_rebuild_threshold=2,
            # no scan_fn
        )

        # 3 events >= threshold, but no scan_fn → individual operations
        events = [
            SpecChangeEvent(
                "modified", Path(f"/tasks/DIA-{i:03d}-x.story.md"), f"DIA-{i:03d}"
            )
            for i in range(1, 4)
        ]
        callback(events)

        cache.rebuild.assert_not_called()
        assert cache.put.call_count == 3

    def test_below_threshold_does_individual_ops(self):
        cache = MagicMock()
        spec = MagicMock()
        parse_fn = MagicMock(return_value=spec)
        scan_fn = MagicMock()

        callback = make_cache_callback(
            cache,
            parse_fn=parse_fn,
            full_rebuild_threshold=10,
            scan_fn=scan_fn,
        )

        events = [
            SpecChangeEvent("modified", Path("/tasks/DIA-001-x.story.md"), "DIA-001"),
            SpecChangeEvent("deleted", Path("/tasks/DIA-002-y.story.md"), "DIA-002"),
        ]
        callback(events)

        scan_fn.assert_not_called()
        cache.rebuild.assert_not_called()
        cache.put.assert_called_once()
        cache.invalidate.assert_called_once_with("DIA-002")
