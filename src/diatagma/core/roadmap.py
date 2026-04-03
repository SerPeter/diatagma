"""Generate ROADMAP.md from current spec state.

Produces a deterministic markdown roadmap with:
- Meta table: total/active/archived/backlog counts
- Epics table: one row per epic with pending/active/done counts
- Current cycle: flat list of specs in .specs/ root
- Next cycle: specs assigned to the next cycle (if cycles enabled)

Auto-generated sections live inside marker fences
(``<!-- diatagma:...:start -->`` / ``<!-- diatagma:...:end -->``).
User prose outside these fences is preserved on regeneration.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

from diatagma.core.models import Cycle, Spec

if TYPE_CHECKING:
    from diatagma.core.config import DiatagmaConfig
    from diatagma.core.store import SpecStore

# ---------------------------------------------------------------------------
# Marker fence helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(
    r"(<!-- diatagma:(?P<tag>[^:]+(?::[^:]+)*):start -->)"
    r".*?"
    r"(<!-- diatagma:(?P=tag):end -->)",
    re.DOTALL,
)

_DONE_STATUSES = frozenset({"done", "cancelled"})
_ACTIVE_STATUSES = frozenset({"in-progress", "in-review"})


def _fence(tag: str, content: str) -> str:
    """Wrap *content* in marker fences for the given tag."""
    return f"<!-- diatagma:{tag}:start -->\n{content}\n<!-- diatagma:{tag}:end -->"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

_ID_NUM_RE = re.compile(r"^[A-Z]{1,5}-(\d{3,})")


def _id_sort_key(spec: Spec) -> tuple[str, int]:
    """Sort specs by prefix then numeric ID."""
    m = _ID_NUM_RE.match(spec.meta.id)
    if m:
        prefix = spec.meta.id[: m.start(1) - 1]
        return (prefix, int(m.group(1)))
    return (spec.meta.id, 0)


def _current_cycle(cycles: list[Cycle], today: date | None = None) -> Cycle | None:
    """Return the cycle whose date range contains *today*.

    Falls back to the most recent past cycle if today is between cycles.
    """
    today = today or date.today()
    # Exact match first
    for c in cycles:
        if c.start <= today <= c.end:
            return c
    # Fallback: most recent past cycle
    past = [c for c in cycles if c.end < today]
    if past:
        return max(past, key=lambda c: c.end)
    # Fallback: earliest future cycle
    future = [c for c in cycles if c.start > today]
    if future:
        return min(future, key=lambda c: c.start)
    return None


def _next_cycle(cycles: list[Cycle], current: Cycle | None) -> Cycle | None:
    """Return the cycle immediately after *current*."""
    if current is None:
        return None
    future = [c for c in cycles if c.start > current.end]
    if future:
        return min(future, key=lambda c: c.start)
    return None


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_meta(
    all_specs: list[Spec],
    active_specs: list[Spec],
    archived_count: int,
    backlog_count: int,
) -> str:
    """Render the meta summary table."""
    lines = [
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total specs | {len(all_specs)} |",
        f"| Active (current cycle) | {len(active_specs)} |",
        f"| Archived | {archived_count} |",
        f"| Backlog | {backlog_count} |",
    ]
    return _fence("meta", "\n".join(lines))


def _render_epics_table(epics: list[Spec], all_specs: list[Spec]) -> str:
    """Render the epics overview table."""
    lines = [
        "| Epic | Status | Pending | Active | Done |",
        "|------|--------|---------|--------|------|",
    ]
    for epic in sorted(epics, key=_id_sort_key):
        children = [s for s in all_specs if s.meta.parent == epic.meta.id]
        pending = sum(
            1
            for s in children
            if s.meta.status not in _DONE_STATUSES
            and s.meta.status not in _ACTIVE_STATUSES
        )
        active = sum(1 for s in children if s.meta.status in _ACTIVE_STATUSES)
        done = sum(1 for s in children if s.meta.status in _DONE_STATUSES)
        lines.append(
            f"| {epic.meta.id}: {epic.meta.title} "
            f"| {epic.meta.status} | {pending} | {active} | {done} |"
        )
    return _fence("epics", "\n".join(lines))


def _render_cycle_specs(specs: list[Spec]) -> str:
    """Render a checkbox list of specs sorted by ID."""
    lines: list[str] = []
    for spec in sorted(specs, key=_id_sort_key):
        check = "x" if spec.meta.status in _DONE_STATUSES else " "
        suffix = " (epic)" if spec.meta.type == "epic" else ""
        lines.append(f"- [{check}] {spec.meta.id}: {spec.meta.title}{suffix}")
    return "\n".join(lines) if lines else "*No specs in this cycle.*"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_roadmap(
    store: SpecStore,
    config: DiatagmaConfig,
    *,
    today: date | None = None,
) -> str:
    """Generate the full ROADMAP.md content.

    If an existing ROADMAP.md exists, user prose outside marker fences is
    preserved. Otherwise a fresh document is generated.
    """
    all_specs = store.list(include_archive=True)
    active_specs = store.list(include_archive=False)
    archived_count = sum(1 for s in all_specs if store.is_archived(s.meta.id))
    backlog_count = (
        len(all_specs)
        - len(active_specs)
        - archived_count
        + len(
            [s for s in active_specs if s.file_path and "backlog" in str(s.file_path)]
        )
    )
    # Simpler: count files in each dir
    backlog_specs = [
        s
        for s in all_specs
        if s.file_path is not None and "backlog" in s.file_path.parts
    ]
    archived_specs = [s for s in all_specs if store.is_archived(s.meta.id)]
    root_specs = [
        s for s in all_specs if s not in archived_specs and s not in backlog_specs
    ]

    backlog_count = len(backlog_specs)
    archived_count = len(archived_specs)

    epics = [s for s in all_specs if s.meta.type == "epic"]

    cycles = config.cycles
    cur = _current_cycle(cycles, today)
    nxt = _next_cycle(cycles, cur)

    # Build sections
    sections: list[str] = ["# Roadmap", ""]

    # Meta
    sections.append(_render_meta(all_specs, root_specs, archived_count, backlog_count))
    sections.append("")

    # Epics
    if epics:
        sections.append("## Epics")
        sections.append("")
        sections.append(_render_epics_table(epics, all_specs))
        sections.append("")

    # Current cycle
    if cycles and cur:
        cycle_specs = [s for s in root_specs if s.meta.cycle == cur.name]
        heading = f"## Current Cycle: {cur.name}"
        sections.append(heading)
        sections.append("")
        sections.append(_fence("cycle:current", _render_cycle_specs(cycle_specs)))
        sections.append("")
    else:
        # No cycles — show all root specs
        sections.append("## Current Cycle")
        sections.append("")
        sections.append(_fence("cycle:current", _render_cycle_specs(root_specs)))
        sections.append("")

    # Next cycle
    if cycles and nxt:
        next_specs = [s for s in root_specs if s.meta.cycle == nxt.name]
        heading = f"## Next Cycle: {nxt.name}"
        sections.append(heading)
        sections.append("")
        sections.append(_fence("cycle:next", _render_cycle_specs(next_specs)))
        sections.append("")

    return "\n".join(sections)


def generate_roadmap_json(
    store: SpecStore,
    config: DiatagmaConfig,
    *,
    today: date | None = None,
) -> dict:
    """Generate roadmap data as a JSON-serializable dict."""
    all_specs = store.list(include_archive=True)
    archived_specs = [s for s in all_specs if store.is_archived(s.meta.id)]
    backlog_specs = [
        s
        for s in all_specs
        if s.file_path is not None and "backlog" in s.file_path.parts
    ]
    root_specs = [
        s for s in all_specs if s not in archived_specs and s not in backlog_specs
    ]

    epics = [s for s in all_specs if s.meta.type == "epic"]
    cycles = config.cycles
    cur = _current_cycle(cycles, today)
    nxt = _next_cycle(cycles, cur)

    def _epic_summary(epic: Spec) -> dict:
        children = [s for s in all_specs if s.meta.parent == epic.meta.id]
        return {
            "id": epic.meta.id,
            "title": epic.meta.title,
            "status": epic.meta.status,
            "pending": sum(
                1
                for s in children
                if s.meta.status not in _DONE_STATUSES
                and s.meta.status not in _ACTIVE_STATUSES
            ),
            "active": sum(1 for s in children if s.meta.status in _ACTIVE_STATUSES),
            "done": sum(1 for s in children if s.meta.status in _DONE_STATUSES),
        }

    def _spec_entry(s: Spec) -> dict:
        return {
            "id": s.meta.id,
            "title": s.meta.title,
            "status": s.meta.status,
            "type": s.meta.type,
        }

    result: dict = {
        "meta": {
            "total": len(all_specs),
            "active": len(root_specs),
            "archived": len(archived_specs),
            "backlog": len(backlog_specs),
        },
        "epics": [_epic_summary(e) for e in sorted(epics, key=_id_sort_key)],
    }

    if cycles and cur:
        cycle_specs = [s for s in root_specs if s.meta.cycle == cur.name]
        result["current_cycle"] = {
            "name": cur.name,
            "start": cur.start.isoformat(),
            "end": cur.end.isoformat(),
            "specs": [_spec_entry(s) for s in sorted(cycle_specs, key=_id_sort_key)],
        }
    else:
        result["current_cycle"] = {
            "name": None,
            "specs": [_spec_entry(s) for s in sorted(root_specs, key=_id_sort_key)],
        }

    if cycles and nxt:
        next_specs = [s for s in root_specs if s.meta.cycle == nxt.name]
        result["next_cycle"] = {
            "name": nxt.name,
            "start": nxt.start.isoformat(),
            "end": nxt.end.isoformat(),
            "specs": [_spec_entry(s) for s in sorted(next_specs, key=_id_sort_key)],
        }

    return result


def update_roadmap_file(
    existing_content: str,
    store: SpecStore,
    config: DiatagmaConfig,
    *,
    today: date | None = None,
) -> str:
    """Update an existing ROADMAP.md, preserving prose outside fences.

    Replaces content inside each ``<!-- diatagma:TAG:start -->`` /
    ``<!-- diatagma:TAG:end -->`` pair with fresh data. Content outside
    fences is untouched. If no fences exist, returns a full regeneration.
    """
    if not _FENCE_RE.search(existing_content):
        return generate_roadmap(store, config, today=today)

    fresh = generate_roadmap(store, config, today=today)

    # Build a map of tag -> fresh content between fences
    fresh_fences: dict[str, str] = {}
    for m in _FENCE_RE.finditer(fresh):
        tag = m.group("tag")
        # Extract content between start and end markers
        start_marker = m.group(1)
        end_marker = m.group(3)
        inner = fresh[m.start() + len(start_marker) : m.end() - len(end_marker)]
        fresh_fences[tag] = inner

    # Replace each fence in existing content with fresh content
    def _replace_fence(m: re.Match) -> str:
        tag = m.group("tag")
        if tag in fresh_fences:
            return f"{m.group(1)}{fresh_fences[tag]}{m.group(3)}"
        return m.group(0)

    return _FENCE_RE.sub(_replace_fence, existing_content)
