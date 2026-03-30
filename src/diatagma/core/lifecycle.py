"""Lifecycle automation — completion metadata, auto-complete, reopening guards, archival.

Orchestrates lifecycle transitions across SpecStore and SpecGraph.
The engine wraps store operations with lifecycle side-effects:
completion metadata, parent auto-completion, and reopening guards.

Key class:
    LifecycleEngine(store, settings)
        .update_status(spec_id, new_status, ..., graph, all_specs) → StatusUpdateResult
        .create_spec(prefix, title, ..., all_specs, **meta) → Spec
        .archive_sprint(sprint_name, ..., all_specs) → ArchiveResult
        .archive_done(..., all_specs) → ArchiveResult
        .validate_consistency(all_specs, ...) → list[ConsistencyIssue]
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from diatagma.core.graph import SpecGraph
from diatagma.core.models import (
    ArchiveResult,
    CompletionContext,
    ConsistencyIssue,
    Settings,
    Spec,
    SpecId,
    Sprint,
    StatusUpdateResult,
)
from diatagma.core.next import get_next
from diatagma.core.store import SpecStore

_TERMINAL_STATUSES = frozenset({"done", "cancelled"})


class LifecycleError(Exception):
    """Raised when a lifecycle guard prevents an operation."""

    def __init__(self, message: str, spec_id: str | None = None) -> None:
        self.spec_id = spec_id
        super().__init__(message)


class LifecycleEngine:
    """Lifecycle automation layer on top of SpecStore.

    The engine holds long-lived references to the store and settings.
    Graph and specs are passed per-call because they change with each
    mutation.
    """

    def __init__(self, store: SpecStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings

    # --- Status updates with completion metadata ---------------------------

    def update_status(
        self,
        spec_id: str,
        new_status: str,
        agent_id: str = "unknown",
        *,
        graph: SpecGraph,
        all_specs: list[Spec],
    ) -> StatusUpdateResult:
        """Update a spec's status and return lifecycle context.

        When the new status is terminal (done/cancelled), builds a
        ``CompletionContext`` with parent progress, newly unblocked specs,
        sprint status, and auto-completes parent epics if applicable.
        """
        updated = self._store.update(spec_id, agent_id=agent_id, status=new_status)

        # Patch in-memory state so subsequent queries reflect the change
        graph.update_node_status(spec_id, new_status)
        _patch_spec_in_list(all_specs, updated)

        if new_status not in _TERMINAL_STATUSES:
            return StatusUpdateResult(spec=updated, completion=None)

        # Build completion context
        auto_completed = self._auto_complete_parents(
            spec_id, agent_id, all_specs, graph
        )

        ctx = CompletionContext(
            parent_progress=_parent_progress(updated, all_specs),
            sprint_progress=_sprint_progress(updated, all_specs),
            sprint_complete=_sprint_complete(updated, all_specs),
            newly_unblocked=_newly_unblocked(spec_id, graph),
            next_ready=[s.meta.id for s in get_next(all_specs, graph, n=5)],
            auto_completed_parents=auto_completed,
        )
        return StatusUpdateResult(spec=updated, completion=ctx)

    # --- Spec creation with reopening guards -------------------------------

    def create_spec(
        self,
        prefix: str,
        title: str,
        agent_id: str = "unknown",
        *,
        reopen: bool = False,
        all_specs: list[Spec] | None = None,
        **meta: Any,
    ) -> Spec:
        """Create a spec with lifecycle guards on parent and sprint.

        Raises ``LifecycleError`` if the parent epic is archived or the
        sprint is complete, unless ``reopen=True``.
        """
        parent_id = meta.get("parent")
        sprint_name = meta.get("sprint")

        if parent_id:
            self._guard_parent(parent_id, agent_id, reopen)

        if sprint_name and all_specs is not None:
            self._guard_sprint(sprint_name, all_specs, reopen)

        return self._store.create(prefix, title, agent_id=agent_id, **meta)

    # --- Batch archival ----------------------------------------------------

    def archive_sprint(
        self,
        sprint_name: str,
        agent_id: str = "unknown",
        *,
        all_specs: list[Spec] | None = None,
    ) -> ArchiveResult:
        """Move all terminal specs in a sprint to archive."""
        if all_specs is None:
            all_specs = self._store.list()

        sprint_specs = [s for s in all_specs if s.meta.sprint == sprint_name]
        return self._archive_specs(sprint_specs, agent_id)

    def archive_done(
        self,
        agent_id: str = "unknown",
        *,
        all_specs: list[Spec] | None = None,
    ) -> ArchiveResult:
        """Move all terminal specs to archive, regardless of sprint."""
        if all_specs is None:
            all_specs = self._store.list()

        terminal = [s for s in all_specs if s.meta.status in _TERMINAL_STATUSES]
        return self._archive_specs(terminal, agent_id, skip_filter=False)

    # --- Consistency validation --------------------------------------------

    def validate_consistency(
        self,
        all_specs: list[Spec] | None = None,
        agent_id: str = "system",
        *,
        sprints: list[Sprint] | None = None,
    ) -> list[ConsistencyIssue]:
        """Check lifecycle invariants and auto-correct where safe.

        Auto-corrects:
            - Done epic with non-terminal children → reopen to in-progress
        Warns only:
            - Completed sprint with non-terminal specs
            - Orphaned children (parent not found)
        """
        if all_specs is None:
            all_specs = self._store.list()

        issues: list[ConsistencyIssue] = []
        specs_by_id = {s.meta.id: s for s in all_specs}

        # Check 1: Done epics with non-terminal children
        issues.extend(self._check_epic_consistency(all_specs, specs_by_id, agent_id))

        # Check 2: Completed sprints with non-terminal specs
        issues.extend(self._check_sprint_consistency(all_specs, sprints))

        # Check 3: Orphaned children
        issues.extend(self._check_orphaned_children(all_specs, specs_by_id))

        return issues

    # --- Internal helpers --------------------------------------------------

    def _auto_complete_parents(
        self,
        spec_id: str,
        agent_id: str,
        all_specs: list[Spec],
        graph: SpecGraph,
    ) -> list[str]:
        """Recursively auto-complete parent epics. Returns auto-completed IDs."""
        if not self._settings.auto_complete_parent:
            return []

        spec = _find_spec(all_specs, spec_id)
        if spec is None or spec.meta.parent is None:
            return []

        parent_id = spec.meta.parent
        parent = _find_spec(all_specs, parent_id)
        if parent is None or parent.meta.status in _TERMINAL_STATUSES:
            return []

        # Check if all children of this parent are terminal
        children = [s for s in all_specs if s.meta.parent == parent_id]
        if not children:
            return []

        all_terminal = all(s.meta.status in _TERMINAL_STATUSES for s in children)
        if not all_terminal:
            return []

        # Auto-complete the parent
        self._store.update(parent_id, agent_id=agent_id, status="done")
        graph.update_node_status(parent_id, "done")
        _patch_status_in_list(all_specs, parent_id, "done")
        logger.info("{} auto-completed (all children done)", parent_id)

        # Recurse upward
        return [parent_id] + self._auto_complete_parents(
            parent_id, agent_id, all_specs, graph
        )

    def _guard_parent(self, parent_id: str, agent_id: str, reopen: bool) -> None:
        """Check parent epic status; reopen or raise as needed."""
        try:
            parent = self._store.get(parent_id)
        except Exception:
            return  # Parent doesn't exist yet — no guard needed

        is_archived = self._store.is_archived(parent_id)

        if parent.meta.status not in _TERMINAL_STATUSES:
            return  # Parent is active — no guard needed

        if is_archived:
            if not reopen:
                raise LifecycleError(
                    f"{parent_id} is archived. Use --reopen to unarchive and reopen it.",
                    spec_id=parent_id,
                )
            self._store.restore_from_archive(parent_id, agent_id)
            self._store.update(parent_id, agent_id=agent_id, status="in-progress")
            logger.info("{} restored from archive and reopened", parent_id)
        else:
            # Done but not archived — auto-reopen
            self._store.update(parent_id, agent_id=agent_id, status="in-progress")
            logger.info("{} reopened (new child added)", parent_id)

    def _guard_sprint(
        self, sprint_name: str, all_specs: list[Spec], reopen: bool
    ) -> None:
        """Check if sprint is complete; raise if so and reopen not set."""
        sprint_specs = [s for s in all_specs if s.meta.sprint == sprint_name]
        if not sprint_specs:
            return  # Empty or unknown sprint — no guard

        all_terminal = all(s.meta.status in _TERMINAL_STATUSES for s in sprint_specs)
        if not all_terminal:
            return

        if not reopen:
            raise LifecycleError(
                f"Sprint '{sprint_name}' is complete. "
                "Assign to a different sprint or use --reopen to reactivate it.",
                spec_id=None,
            )

    def _archive_specs(
        self,
        specs: list[Spec],
        agent_id: str,
        skip_filter: bool = True,
    ) -> ArchiveResult:
        """Archive terminal specs from a list, skip non-terminal."""
        archived: list[str] = []
        skipped: list[str] = []
        warnings: list[str] = []

        for spec in specs:
            if skip_filter and spec.meta.status not in _TERMINAL_STATUSES:
                skipped.append(spec.meta.id)
                warnings.append(
                    f"{spec.meta.id} is {spec.meta.status}, skipping archive"
                )
                continue
            self._store.move_to_archive(spec.meta.id, agent_id)
            archived.append(spec.meta.id)

        if skipped:
            logger.warning(
                "skipped {} non-terminal specs during archive: {}",
                len(skipped),
                skipped,
            )

        return ArchiveResult(archived=archived, skipped=skipped, warnings=warnings)

    def _check_epic_consistency(
        self,
        all_specs: list[Spec],
        specs_by_id: dict[str, Spec],
        agent_id: str,
    ) -> list[ConsistencyIssue]:
        """Detect done epics with non-terminal children; auto-reopen."""
        issues: list[ConsistencyIssue] = []

        # Build children lookup
        children_by_parent: dict[str, list[Spec]] = {}
        for spec in all_specs:
            if spec.meta.parent:
                children_by_parent.setdefault(spec.meta.parent, []).append(spec)

        for epic_id, children in children_by_parent.items():
            epic = specs_by_id.get(epic_id)
            if epic is None:
                continue
            if epic.meta.status not in _TERMINAL_STATUSES:
                continue
            if epic.meta.type != "epic":
                continue

            non_terminal = [
                c for c in children if c.meta.status not in _TERMINAL_STATUSES
            ]
            if not non_terminal:
                continue

            # Auto-reopen
            child_ids = ", ".join(c.meta.id for c in non_terminal)
            msg = f"{epic_id} reopened (non-terminal children detected: {child_ids})"
            self._store.update(epic_id, agent_id=agent_id, status="in-progress")
            logger.info(msg)

            issues.append(
                ConsistencyIssue(
                    type="epic_done_with_active_children",
                    spec_id=epic_id,
                    message=msg,
                    auto_corrected=True,
                )
            )

        return issues

    def _check_sprint_consistency(
        self,
        all_specs: list[Spec],
        sprints: list[Sprint] | None,
    ) -> list[ConsistencyIssue]:
        """Detect completed sprints with non-terminal specs."""
        issues: list[ConsistencyIssue] = []

        # Group specs by sprint
        by_sprint: dict[str, list[Spec]] = {}
        for spec in all_specs:
            if spec.meta.sprint:
                by_sprint.setdefault(spec.meta.sprint, []).append(spec)

        for sprint_name, sprint_specs in by_sprint.items():
            terminal = [s for s in sprint_specs if s.meta.status in _TERMINAL_STATUSES]
            non_terminal = [
                s for s in sprint_specs if s.meta.status not in _TERMINAL_STATUSES
            ]

            # Only flag if there's a mix AND the sprint has an end date that's passed
            if not terminal or not non_terminal:
                continue

            # If we have sprint definitions, check if the sprint has ended
            if sprints:
                sprint_def = next(
                    (sp for sp in sprints if sp.name == sprint_name), None
                )
                if sprint_def is None:
                    continue  # Unknown sprint — skip

            non_terminal_ids = ", ".join(s.meta.id for s in non_terminal)
            msg = f"Sprint '{sprint_name}' has non-terminal specs: {non_terminal_ids}"
            logger.warning(msg)

            issues.append(
                ConsistencyIssue(
                    type="sprint_complete_with_active",
                    spec_id=sprint_name,
                    message=msg,
                    auto_corrected=False,
                )
            )

        return issues

    def _check_orphaned_children(
        self,
        all_specs: list[Spec],
        specs_by_id: dict[str, Spec],
    ) -> list[ConsistencyIssue]:
        """Detect specs whose parent ID doesn't exist."""
        issues: list[ConsistencyIssue] = []

        for spec in all_specs:
            if spec.meta.parent and spec.meta.parent not in specs_by_id:
                msg = (
                    f"{spec.meta.id} has parent {spec.meta.parent} which does not exist"
                )
                logger.warning(msg)
                issues.append(
                    ConsistencyIssue(
                        type="orphaned_child",
                        spec_id=spec.meta.id,
                        message=msg,
                        auto_corrected=False,
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _find_spec(specs: list[Spec], spec_id: str) -> Spec | None:
    """Find a spec by ID in a list."""
    for s in specs:
        if s.meta.id == spec_id:
            return s
    return None


def _patch_spec_in_list(specs: list[Spec], updated: Spec) -> None:
    """Replace a spec in a list with an updated version."""
    for i, s in enumerate(specs):
        if s.meta.id == updated.meta.id:
            specs[i] = updated
            return


def _patch_status_in_list(specs: list[Spec], spec_id: str, status: str) -> None:
    """Update a spec's status in-place within a list."""
    for s in specs:
        if s.meta.id == spec_id:
            meta_dict = s.meta.model_dump()
            meta_dict["status"] = status
            from diatagma.core.models import SpecMeta

            s.meta = SpecMeta.model_validate(meta_dict)
            return


def _parent_progress(spec: Spec, all_specs: list[Spec]) -> str | None:
    """Build parent progress string like '4/8 stories in DIA-011 done'."""
    if not spec.meta.parent:
        return None

    parent_id = spec.meta.parent
    siblings = [s for s in all_specs if s.meta.parent == parent_id]
    if not siblings:
        return None

    done_count = sum(1 for s in siblings if s.meta.status in _TERMINAL_STATUSES)
    return f"{done_count}/{len(siblings)} stories in {parent_id} done"


def _sprint_progress(spec: Spec, all_specs: list[Spec]) -> str | None:
    """Build sprint progress string like '6/10 specs in Sprint 1 done'."""
    if not spec.meta.sprint:
        return None

    sprint_specs = [s for s in all_specs if s.meta.sprint == spec.meta.sprint]
    if not sprint_specs:
        return None

    done_count = sum(1 for s in sprint_specs if s.meta.status in _TERMINAL_STATUSES)
    return f"{done_count}/{len(sprint_specs)} specs in {spec.meta.sprint} done"


def _sprint_complete(spec: Spec, all_specs: list[Spec]) -> bool:
    """True if all specs in the spec's sprint are terminal."""
    if not spec.meta.sprint:
        return False

    sprint_specs = [s for s in all_specs if s.meta.sprint == spec.meta.sprint]
    if not sprint_specs:
        return False

    return all(s.meta.status in _TERMINAL_STATUSES for s in sprint_specs)


def _newly_unblocked(spec_id: str, graph: SpecGraph) -> list[SpecId]:
    """Find specs that became unblocked by this spec's completion."""
    unblocked: list[str] = []
    for dep_id in graph.get_dependents(spec_id):
        if not graph.is_blocked(dep_id):
            unblocked.append(dep_id)
    return sorted(unblocked)


__all__ = [
    "LifecycleEngine",
    "LifecycleError",
]
