"""Detect and resolve spec ID collisions after git merge.

When branches create specs independently, they may assign the same ID.
This module provides detection (scan for duplicates), resolution
(renumber a spec and update all cross-references), and auto-fix
(keep the older file's ID, reassign the newer one).
"""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from diatagma.core.models import ConsistencyIssue, DuplicateGroup
from diatagma.core.parser import parse_spec_file, write_spec_file

if TYPE_CHECKING:
    from diatagma.core.store import SpecStore

_ID_RE = re.compile(r"^([A-Z]{1,5}-\d{3,})")
"""Extract the spec ID prefix from a filename."""


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_duplicate_ids(store: SpecStore) -> list[DuplicateGroup]:
    """Scan all spec files, return groups where 2+ files share the same ID."""
    id_to_paths: dict[str, list[Path]] = defaultdict(list)
    for path in store.scan_files():
        m = _ID_RE.match(path.name)
        if m:
            id_to_paths[m.group(1)].append(path)

    duplicates: list[DuplicateGroup] = []
    for spec_id, paths in sorted(id_to_paths.items()):
        if len(paths) >= 2:
            slugs = [_extract_slug(p.name, spec_id) for p in paths]
            duplicates.append(DuplicateGroup(spec_id=spec_id, files=paths, slugs=slugs))
    return duplicates


def _extract_slug(filename: str, spec_id: str) -> str:
    """Extract the slug portion from a spec filename.

    ``"DIA-021-api-caching.story.md"`` → ``"api-caching"``
    """
    # Strip the ID prefix and hyphen, then strip the extension(s)
    rest = filename[len(spec_id) + 1 :]  # "api-caching.story.md"
    # Remove .TYPE.md or .md suffix
    rest = re.sub(r"\.\w+\.md$", "", rest)
    return rest


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def renumber_spec(
    old_id: str,
    new_id: str,
    file_path: Path,
    store: SpecStore,
) -> list[str]:
    """Rename a spec file, update its frontmatter ID, and update all references.

    Returns a list of warning messages for ambiguous references.
    """
    warnings: list[str] = []

    # 1. Parse the spec at file_path
    spec = parse_spec_file(file_path)

    # 2. Update the spec's ID
    spec.meta = spec.meta.model_copy(update={"id": new_id})

    # 3. Compute new filename (replace old ID prefix with new)
    new_filename = new_id + file_path.name[len(old_id) :]
    new_path = file_path.parent / new_filename

    # 4. Write to new path, delete old file
    write_spec_file(spec, new_path)
    if file_path != new_path:
        file_path.unlink()

    # 5. Check if old_id is still ambiguous (other files still have it)
    remaining = _count_files_with_id(store, old_id, exclude=new_path)
    ambiguous = remaining >= 1  # Another file still has old_id

    # 6. Update references across all specs
    for path in store.scan_files():
        if path == new_path:
            continue
        try:
            other = parse_spec_file(path)
        except Exception:
            continue

        if ambiguous and _spec_references_id(other, old_id):
            warnings.append(
                f"{other.meta.id} references {old_id} which was duplicated "
                f"-- verify reference still points to the intended spec"
            )
            continue

        if _replace_id_in_spec(other, old_id, new_id):
            write_spec_file(other, path)

    return warnings


def auto_fix_duplicates(
    store: SpecStore,
    duplicates: list[DuplicateGroup],
) -> tuple[list[ConsistencyIssue], list[str]]:
    """Auto-renumber duplicates: keep older file's ID, assign next_id() to newer.

    Returns (issues, warnings).
    """
    issues: list[ConsistencyIssue] = []
    all_warnings: list[str] = []

    for group in duplicates:
        # Sort by age: oldest first
        sorted_files = sorted(group.files, key=_file_age)

        # Keep the oldest file's ID, renumber the rest
        for file_path in sorted_files[1:]:
            prefix = group.spec_id.rsplit("-", 1)[0]
            new_id = store.next_id(prefix)
            slug = _extract_slug(file_path.name, group.spec_id)

            warnings = renumber_spec(group.spec_id, new_id, file_path, store)
            all_warnings.extend(warnings)

            issues.append(
                ConsistencyIssue(
                    type="duplicate_id",
                    spec_id=group.spec_id,
                    message=(
                        f"Duplicate ID {group.spec_id}: renumbered {slug} to {new_id}"
                    ),
                    auto_corrected=True,
                )
            )

    return issues, all_warnings


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _file_age(path: Path) -> datetime:
    """Return the git commit timestamp when the file was first added.

    Falls back to filesystem mtime if git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(path.parent),
        )
        if result.returncode == 0 and result.stdout.strip():
            # Take the last line (earliest commit that added the file)
            ts = result.stdout.strip().splitlines()[-1]
            return datetime.fromisoformat(ts)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _count_files_with_id(store: SpecStore, spec_id: str, exclude: Path) -> int:
    """Count how many files still have the given spec ID prefix."""
    prefix = f"{spec_id}-"
    count = 0
    for path in store.scan_files():
        if path != exclude and path.name.startswith(prefix):
            count += 1
    return count


def _spec_references_id(spec: "SpecStore | object", old_id: str) -> bool:
    """Check if a spec references the given ID in any link/parent field."""
    from diatagma.core.models import Spec

    if not isinstance(spec, Spec):
        return False
    meta = spec.meta
    if meta.parent == old_id:
        return True
    links = meta.links
    return (
        old_id in links.blocked_by
        or old_id in links.relates_to
        or old_id in links.supersedes
        or links.discovered_from == old_id
    )


def _replace_id_in_spec(spec: object, old_id: str, new_id: str) -> bool:
    """Replace old_id with new_id in all reference fields of a spec.

    Builds new frozen model instances. Returns True if anything changed.
    """
    from diatagma.core.models import Spec

    if not isinstance(spec, Spec):
        return False

    changed = False
    meta = spec.meta
    links = meta.links

    # Parent
    new_parent = meta.parent
    if meta.parent == old_id:
        new_parent = new_id
        changed = True

    # Links
    new_blocked_by = _replace_in_list(links.blocked_by, old_id, new_id)
    new_relates_to = _replace_in_list(links.relates_to, old_id, new_id)
    new_supersedes = _replace_in_list(links.supersedes, old_id, new_id)
    new_discovered = links.discovered_from
    if links.discovered_from == old_id:
        new_discovered = new_id

    if (
        new_blocked_by != links.blocked_by
        or new_relates_to != links.relates_to
        or new_supersedes != links.supersedes
        or new_discovered != links.discovered_from
    ):
        changed = True

    if changed:
        new_links = links.model_copy(
            update={
                "blocked_by": new_blocked_by,
                "relates_to": new_relates_to,
                "supersedes": new_supersedes,
                "discovered_from": new_discovered,
            }
        )
        spec.meta = meta.model_copy(update={"parent": new_parent, "links": new_links})

    return changed


def _replace_in_list(items: list[str], old: str, new: str) -> list[str]:
    """Replace occurrences of old with new in a list."""
    return [new if item == old else item for item in items]
