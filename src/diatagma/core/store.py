"""SpecStore — CRUD operations over the .tasks/ directory.

The single source-of-truth layer. Every read/write goes through the
filesystem. The store discovers spec files by scanning configured
directories, delegates parsing to parser.py, and coordinates with
cache.py for acceleration.

File extensions determine spec type:
    .story.md  — stories (features, bugs, chores, docs)
    .epic.md   — epics
    .spike.md  — research spikes

Key class:
    SpecStore(tasks_dir: Path)
        .list(filters, sort_by)  → list[Spec]
        .get(spec_id)            → Spec
        .create(prefix, title, spec_type, template, **meta) → Spec
        .update(spec_id, **changes)
        .move_to_backlog(spec_id)
        .move_to_archive(spec_id)
        .next_id(prefix)         → str  (e.g. "DIA-004")
"""

from __future__ import annotations

import builtins
import re
import shutil
import threading
from collections import defaultdict
from datetime import date
from pathlib import Path
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from loguru import logger
from pydantic import ValidationError

from diatagma.core.models import (
    PrefixDef,
    Settings,
    SortField,
    Spec,
    SpecBody,
    SpecFilter,
    SpecMeta,
)
from diatagma.core.parser import ParseError, parse_spec_file, write_spec_file

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SPEC_FILE_RE = re.compile(r"^[A-Z]{1,5}-\d{3,}-.+\.\w+\.md$")
"""Regex matching spec filenames: PREFIX-NNN-slug.type.md"""

_TYPE_TO_EXT: dict[str, str] = {
    "epic": ".epic.md",
    "spike": ".spike.md",
}
"""Spec type → file extension. Everything else defaults to .story.md."""

_DEFAULT_EXT = ".story.md"

# ---------------------------------------------------------------------------
# Helper types
# ---------------------------------------------------------------------------


@runtime_checkable
class ChangelogCallback(Protocol):
    """Protocol for mutation logging. Implemented by DIA-007."""

    def __call__(
        self,
        spec_id: str,
        action: str,
        field: str | None = None,
        old: str | None = None,
        new: str | None = None,
        agent_id: str = "unknown",
    ) -> None: ...


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StoreError(Exception):
    """Base exception for store operations."""


class SpecNotFoundError(StoreError):
    """Raised when a spec ID cannot be found in any directory."""

    def __init__(self, spec_id: str) -> None:
        self.spec_id = spec_id
        super().__init__(f"spec not found: {spec_id}")


class InvalidPrefixError(StoreError):
    """Raised when a prefix is not configured."""

    def __init__(self, prefix: str, valid: list[str]) -> None:
        self.prefix = prefix
        self.valid = valid
        super().__init__(
            f"unknown prefix {prefix!r}, valid prefixes: {', '.join(valid)}"
        )


# ---------------------------------------------------------------------------
# Slug helper
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^\w\s-]")
_SLUG_SEP_RE = re.compile(r"[\s_]+")


def _slugify(title: str, max_length: int = 50) -> str:
    """Convert a title to a URL/filename-safe slug.

    ``"Implement TaskStore CRUD"`` → ``"implement-taskstore-crud"``
    """
    slug = _SLUG_RE.sub("", title.lower())
    slug = _SLUG_SEP_RE.sub("-", slug).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]
    return slug


# ---------------------------------------------------------------------------
# ID extraction helper
# ---------------------------------------------------------------------------

_ID_NUM_RE = re.compile(r"^([A-Z]{1,5})-(\d{3,})")


def _extract_id_number(filename: str, prefix: str) -> int | None:
    """Extract the numeric part of a spec ID from a filename.

    Returns None if the filename doesn't match the given prefix.
    """
    m = _ID_NUM_RE.match(filename)
    if m and m.group(1) == prefix:
        return int(m.group(2))
    return None


# ---------------------------------------------------------------------------
# Sort helpers
# ---------------------------------------------------------------------------


def _id_sort_key(spec: Spec) -> tuple[str, int]:
    """Sort key that orders by prefix alphabetically, then by number."""
    m = _ID_NUM_RE.match(spec.meta.id)
    if m:
        return (m.group(1), int(m.group(2)))
    return (spec.meta.id, 0)


def _sort_key(spec: Spec, field: SortField) -> Any:
    """Return a comparable sort key for the given field."""
    match field:
        case SortField.ID:
            return _id_sort_key(spec)
        case SortField.TITLE:
            return spec.meta.title.lower()
        case SortField.STATUS:
            return spec.meta.status
        case SortField.CREATED:
            return spec.meta.created
        case SortField.UPDATED:
            return spec.meta.updated or date.min
        case SortField.BUSINESS_VALUE:
            return (
                spec.meta.business_value
                if spec.meta.business_value is not None
                else -9999
            )
        case SortField.STORY_POINTS:
            return spec.meta.story_points if spec.meta.story_points is not None else 0
        case SortField.PRIORITY:
            return spec.priority_score
        case _:  # pragma: no cover
            return spec.meta.id


# ---------------------------------------------------------------------------
# SpecStore
# ---------------------------------------------------------------------------


class SpecStore:
    """CRUD operations over the .tasks/ directory.

    The store scans the tasks directory (plus backlog/ and archive/
    subdirectories) for spec files, delegates parsing to parser.py,
    and provides filtering, sorting, creation, update, and move
    operations.
    """

    def __init__(
        self,
        tasks_dir: Path,
        prefixes: dict[str, PrefixDef],
        templates: dict[str, str],
        settings: Settings | None = None,
        on_mutation: Callable[..., Any] | None = None,
    ) -> None:
        self._tasks_dir = Path(tasks_dir)
        self._backlog_dir = self._tasks_dir / "backlog"
        self._archive_dir = self._tasks_dir / "archive"
        self._prefixes = prefixes
        self._templates = templates
        self._settings = settings or Settings()
        self._on_mutation = on_mutation

        # Concurrency guards
        self._id_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._create_lock = threading.Lock()

    # --- Read operations ---------------------------------------------------

    def list(
        self,
        filters: SpecFilter | None = None,
        sort_by: SortField = SortField.ID,
        reverse: bool = False,
    ) -> builtins.list[Spec]:
        """Discover and return specs from all directories.

        Broken files are logged and skipped.
        """
        specs: builtins.list[Spec] = []
        for path in self._scan_dirs():
            try:
                specs.append(parse_spec_file(path))
            except (ParseError, ValidationError, OSError) as exc:
                logger.warning("skipping {}: {}", path.name, exc)

        if filters is not None:
            specs = self._apply_filters(specs, filters)

        specs.sort(key=lambda s: _sort_key(s, sort_by), reverse=reverse)
        return specs

    def get(self, spec_id: str) -> Spec:
        """Find and parse a single spec by ID."""
        path = self._find_spec_file(spec_id)
        return parse_spec_file(path)

    # --- Write operations --------------------------------------------------

    def create(
        self,
        prefix: str,
        title: str,
        spec_type: str = "feature",
        template: str | None = None,
        agent_id: str = "unknown",
        **meta: Any,
    ) -> Spec:
        """Generate next ID, write a new spec file from template."""
        self._validate_prefix(prefix)

        with self._create_lock:
            spec_id = self.next_id(prefix)

            # Resolve template
            template_name = template or self._prefixes[prefix].template
            template_body = self._templates.get(template_name, "")

            # Build filename and path
            filename = self._build_filename(spec_id, title, spec_type)
            target_path = self._tasks_dir / filename

            # Build metadata
            meta_dict: dict[str, Any] = {
                "id": spec_id,
                "title": title,
                "status": "pending",
                "type": spec_type,
                "created": date.today(),
                **meta,
            }
            spec_meta = SpecMeta.model_validate(meta_dict)

            # Build and write spec
            spec = Spec(
                meta=spec_meta,
                raw_body=template_body if template_body else None,
                file_path=target_path,
            )
            write_spec_file(spec, target_path)

        self._log_mutation(spec_id, "created", agent_id=agent_id)
        return spec

    def update(
        self,
        spec_id: str,
        agent_id: str = "unknown",
        **changes: Any,
    ) -> Spec:
        """Modify frontmatter and/or body fields, write back."""
        with self._id_locks[spec_id]:
            spec = self.get(spec_id)

            meta_fields = set(SpecMeta.model_fields)
            body_fields = {
                name for name in SpecBody.model_fields if name != "extra_sections"
            }

            meta_changes: dict[str, Any] = {}
            body_changes: dict[str, Any] = {}

            for key, value in changes.items():
                if key in meta_fields:
                    meta_changes[key] = value
                elif key in body_fields:
                    body_changes[key] = value
                elif key == "extra_sections":
                    body_changes[key] = value
                else:
                    logger.warning("ignoring unknown field in update: {}", key)

            # Apply meta changes
            if meta_changes:
                current_meta = spec.meta.model_dump()
                old_values = {k: current_meta.get(k) for k in meta_changes}
                current_meta.update(meta_changes)
                current_meta["updated"] = date.today()
                spec.meta = SpecMeta.model_validate(current_meta)

                # Log each changed field
                for field_name, new_val in meta_changes.items():
                    old_val = old_values.get(field_name)
                    if old_val != new_val:
                        self._log_mutation(
                            spec_id,
                            "updated",
                            field=field_name,
                            old=str(old_val) if old_val is not None else None,
                            new=str(new_val) if new_val is not None else None,
                            agent_id=agent_id,
                        )

            # Apply body changes
            if body_changes:
                current_body = spec.body.model_dump()
                for field_name, new_val in body_changes.items():
                    old_val = current_body.get(field_name)
                    current_body[field_name] = new_val
                    if old_val != new_val:
                        self._log_mutation(
                            spec_id,
                            "updated",
                            field=field_name,
                            old="(body)" if old_val else None,
                            new="(body)" if new_val else None,
                            agent_id=agent_id,
                        )
                spec.body = SpecBody.model_validate(current_body)
                # Clear raw_body to force re-render from structured body
                spec.raw_body = None

                # Also set updated date if not already set by meta changes
                if not meta_changes:
                    current_meta = spec.meta.model_dump()
                    current_meta["updated"] = date.today()
                    spec.meta = SpecMeta.model_validate(current_meta)

            if spec.file_path is None:
                raise StoreError(f"spec {spec_id} has no file_path")
            write_spec_file(spec, spec.file_path)
            return spec

    def move_to_backlog(self, spec_id: str, agent_id: str = "unknown") -> Spec:
        """Move a spec file to the backlog/ directory."""
        return self._move_spec(spec_id, self._backlog_dir, "backlog", agent_id)

    def move_to_archive(self, spec_id: str, agent_id: str = "unknown") -> Spec:
        """Move a spec file to the archive/ directory."""
        spec = self.get(spec_id)
        if not spec.body.implementation_summary:
            logger.warning(
                "archiving {} without an ## Implementation Summary section", spec_id
            )
        return self._move_spec(spec_id, self._archive_dir, "archive", agent_id)

    # --- ID generation -----------------------------------------------------

    def next_id(self, prefix: str) -> str:
        """Scan existing files to determine the next sequential ID.

        Returns e.g. ``"DIA-004"`` (zero-padded to 3 digits minimum).
        """
        self._validate_prefix(prefix)

        max_num = 0
        for path in self._scan_dirs():
            num = _extract_id_number(path.name, prefix)
            if num is not None and num > max_num:
                max_num = num

        next_num = max_num + 1
        return f"{prefix}-{next_num:03d}"

    # --- Internal helpers --------------------------------------------------

    def _scan_dirs(self) -> builtins.list[Path]:
        """Glob for spec files in tasks_dir, backlog/, and archive/."""
        paths: builtins.list[Path] = []
        for directory in (self._tasks_dir, self._backlog_dir, self._archive_dir):
            if not directory.exists():
                continue
            for p in directory.glob("*.md"):
                if _SPEC_FILE_RE.match(p.name):
                    paths.append(p)
        return sorted(paths)

    def _find_spec_file(self, spec_id: str) -> Path:
        """Find a spec file by ID across all directories."""
        prefix = f"{spec_id}-"
        for path in self._scan_dirs():
            if path.name.startswith(prefix):
                return path
        raise SpecNotFoundError(spec_id)

    def _validate_prefix(self, prefix: str) -> None:
        """Raise InvalidPrefixError if prefix is not configured."""
        if prefix not in self._prefixes:
            raise InvalidPrefixError(prefix, list(self._prefixes.keys()))

    def _build_filename(self, spec_id: str, title: str, spec_type: str) -> str:
        """Build a spec filename from ID, title, and type."""
        ext = _TYPE_TO_EXT.get(spec_type, _DEFAULT_EXT)
        slug = _slugify(title)
        return f"{spec_id}-{slug}{ext}"

    def _move_spec(
        self, spec_id: str, target_dir: Path, label: str, agent_id: str
    ) -> Spec:
        """Move a spec file to a target directory."""
        with self._id_locks[spec_id]:
            src_path = self._find_spec_file(spec_id)
            dest_path = target_dir / src_path.name

            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dest_path))

            self._log_mutation(spec_id, f"moved to {label}", agent_id=agent_id)

            return parse_spec_file(dest_path)

    def _apply_filters(
        self, specs: builtins.list[Spec], filters: SpecFilter
    ) -> builtins.list[Spec]:
        """Filter specs in-memory based on SpecFilter criteria."""
        result: builtins.list[Spec] = []

        for spec in specs:
            if not self._matches_filter(spec, filters):
                continue
            result.append(spec)

        return result

    @staticmethod
    def _matches_filter(spec: Spec, f: SpecFilter) -> bool:
        """Check if a spec matches all non-None filter criteria."""
        if f.status is not None:
            allowed = {f.status} if isinstance(f.status, str) else set(f.status)
            if spec.meta.status not in allowed:
                return False

        if f.type is not None:
            allowed = {f.type} if isinstance(f.type, str) else set(f.type)
            if spec.meta.type not in allowed:
                return False

        if f.tags is not None:
            if not set(f.tags) & set(spec.meta.tags):
                return False

        if f.prefix is not None:
            if not spec.meta.id.startswith(f.prefix + "-"):
                return False

        if f.parent is not None:
            if spec.meta.parent != f.parent:
                return False

        if f.assignee is not None:
            if spec.meta.assignee != f.assignee:
                return False

        if f.sprint is not None:
            if spec.meta.sprint != f.sprint:
                return False

        if f.search is not None:
            if f.search.lower() not in spec.meta.title.lower():
                return False

        return True

    def _log_mutation(self, spec_id: str, action: str, **kwargs: Any) -> None:
        """Invoke the changelog callback if configured."""
        if self._on_mutation is not None:
            self._on_mutation(spec_id, action, **kwargs)


__all__ = [
    "ChangelogCallback",
    "InvalidPrefixError",
    "SortField",
    "SpecFilter",
    "SpecNotFoundError",
    "SpecStore",
    "StoreError",
]
