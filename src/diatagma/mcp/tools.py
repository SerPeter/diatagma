"""MCP tool definitions — thin wrappers over core library functions.

Reads go through the SQLite cache (mtime-validated) for performance.
Mutations go through SpecStore, then update the cache. Each tool call
is still stateless — the cache is on-disk, not in-memory.

Key function:
    register_tools(mcp, specs_dir, cache) → None
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from fastmcp import FastMCP

from diatagma.core.cache import SpecCache
from diatagma.core.context import create_context
from diatagma.core.models import Spec, SpecFilter, SortField
from diatagma.core.next import get_next


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _spec_summary(spec: Spec) -> dict:
    """Compact spec dict for list operations (meta fields + score)."""
    d = spec.meta.model_dump(mode="json", exclude_none=True)
    if spec.priority_score:
        d["priority_score"] = round(spec.priority_score, 1)
    if spec.is_blocked:
        d["is_blocked"] = True
    return d


def _spec_detail(spec: Spec) -> dict:
    """Full spec dict for single-item operations."""
    d: dict = {"meta": spec.meta.model_dump(mode="json", exclude_none=True)}
    body = spec.body.model_dump(exclude_none=True)
    body.pop("extra_sections", None)
    if body:
        d["body"] = body
    if spec.priority_score:
        d["priority_score"] = round(spec.priority_score, 1)
    if spec.is_blocked:
        d["is_blocked"] = True
    return d


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode()


def _decode_cursor(cursor: str) -> int:
    try:
        return json.loads(base64.urlsafe_b64decode(cursor))["o"]
    except Exception:
        return 0


def _parse_tags(tags: str | None) -> list[str] | None:
    """Parse comma-separated tags string into a list."""
    if not tags:
        return None
    return [t.strip() for t in tags.split(",") if t.strip()]


# ---------------------------------------------------------------------------
# Cache warming
# ---------------------------------------------------------------------------

_warmed_caches: set[int] = set()
"""Track which cache instances have been warmed (by id)."""


def _ensure_warm(cache: SpecCache, specs_dir: Path) -> None:
    """Warm the cache on first use by rebuilding from the filesystem."""
    cache_id = id(cache)
    if cache_id in _warmed_caches:
        return
    ctx = create_context(specs_dir)
    specs = ctx.store.list()
    cache.rebuild(specs)
    _warmed_caches.add(cache_id)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP, specs_dir: Path, cache: SpecCache) -> None:
    """Register all MCP tools on the server instance."""

    @mcp.tool(
        description="Retrieve a single spec by ID with full content.",
        annotations={"readOnlyHint": True},
    )
    def get_spec(spec_id: str) -> dict:
        """Get full spec content including metadata and body sections."""
        ctx = create_context(specs_dir)
        spec = ctx.store.get(spec_id)
        return _spec_detail(spec)

    @mcp.tool(
        description="List specs with optional filters and sorting. "
        "Returns paginated results with a cursor for the next page.",
        annotations={"readOnlyHint": True},
    )
    def list_specs(
        status: str | None = None,
        type: str | None = None,
        tags: str | None = None,
        prefix: str | None = None,
        parent: str | None = None,
        assignee: str | None = None,
        cycle: str | None = None,
        sort_by: str = "id",
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict:
        """List and filter specs. Tags are comma-separated. Returns specs and next_cursor."""
        _ensure_warm(cache, specs_dir)

        filters = SpecFilter(
            status=status,
            type=type,
            tags=_parse_tags(tags),
            prefix=prefix,
            parent=parent,
            assignee=assignee,
            cycle=cycle,
        )

        try:
            sort_field = SortField(sort_by)
        except ValueError:
            sort_field = SortField.ID

        all_specs = cache.query(filters=filters, sort_by=sort_field)

        offset = _decode_cursor(cursor) if cursor else 0
        page = all_specs[offset : offset + limit]
        next_cursor = (
            _encode_cursor(offset + limit) if offset + limit < len(all_specs) else None
        )

        return {
            "specs": [_spec_summary(s) for s in page],
            "total": len(all_specs),
            "next_cursor": next_cursor,
        }

    @mcp.tool(
        description="Get actionable specs ranked by priority. "
        "Returns only unblocked specs with all dependencies satisfied.",
        annotations={"readOnlyHint": True},
    )
    def get_ready_specs(
        limit: int = 10,
        tags: str | None = None,
        type: str | None = None,
        cycle: str | None = None,
    ) -> list[dict]:
        """Priority-sorted list of specs ready to work on."""
        _ensure_warm(cache, specs_dir)

        # get_next needs graph + full spec list — use cache for the list,
        # then build graph from it
        ctx = create_context(specs_dir)
        all_specs = cache.query()
        ctx.graph.build(all_specs)

        ready = get_next(
            all_specs,
            ctx.graph,
            n=limit,
            tags=_parse_tags(tags),
            type=type,
            cycle=cycle,
            config=ctx.config.priority,
        )
        return [_spec_summary(s) for s in ready]

    @mcp.tool(
        description="Create a new spec from template with validated frontmatter.",
    )
    def create_spec(
        title: str,
        prefix: str | None = None,
        type: str = "feature",
        tags: str | None = None,
        business_value: int | None = None,
        story_points: int | None = None,
        parent: str | None = None,
        cycle: str | None = None,
        agent_id: str = "mcp-agent",
    ) -> dict:
        """Create a spec. Prefix defaults to first configured prefix."""
        ctx = create_context(specs_dir)
        all_specs = ctx.refresh_graph()

        resolved_prefix = prefix or next(iter(ctx.config.prefixes), None)
        if resolved_prefix is None:
            raise ValueError("No prefixes configured. Run 'diatagma init' first.")

        extra: dict = {}
        if _parse_tags(tags):
            extra["tags"] = _parse_tags(tags)
        if business_value is not None:
            extra["business_value"] = business_value
        if story_points is not None:
            extra["story_points"] = story_points
        if parent:
            extra["parent"] = parent
        if cycle:
            extra["cycle"] = cycle

        spec = ctx.lifecycle.create_spec(
            resolved_prefix,
            title,
            agent_id=agent_id,
            all_specs=all_specs,
            spec_type=type,
            **extra,
        )
        cache.put(spec)
        return _spec_detail(spec)

    @mcp.tool(
        description="Modify a spec's frontmatter fields and/or body sections.",
    )
    def update_spec(
        spec_id: str,
        title: str | None = None,
        status: str | None = None,
        tags: str | None = None,
        business_value: int | None = None,
        story_points: int | None = None,
        assignee: str | None = None,
        cycle: str | None = None,
        description: str | None = None,
        agent_id: str = "mcp-agent",
    ) -> dict:
        """Update spec fields. Only provided fields are changed."""
        ctx = create_context(specs_dir)

        changes: dict = {}
        if title is not None:
            changes["title"] = title
        if status is not None:
            changes["status"] = status
        if tags is not None:
            changes["tags"] = _parse_tags(tags) or []
        if business_value is not None:
            changes["business_value"] = business_value
        if story_points is not None:
            changes["story_points"] = story_points
        if assignee is not None:
            changes["assignee"] = assignee
        if cycle is not None:
            changes["cycle"] = cycle
        if description is not None:
            changes["description"] = description

        if not changes:
            raise ValueError("No fields to update.")

        spec = ctx.store.update(spec_id, agent_id=agent_id, **changes)
        cache.put(spec)
        return _spec_detail(spec)

    @mcp.tool(
        description="Claim a spec for work. Sets assignee and status to in-progress. "
        "Fails if already claimed by another agent.",
    )
    def claim_spec(
        spec_id: str,
        agent_id: str = "mcp-agent",
    ) -> dict:
        """Claim a spec for exclusive work."""
        ctx = create_context(specs_dir)
        spec = ctx.store.get(spec_id)

        if spec.meta.assignee and spec.meta.assignee != agent_id:
            raise ValueError(f"{spec_id} is already claimed by {spec.meta.assignee!r}.")

        updated = ctx.store.update(
            spec_id,
            agent_id=agent_id,
            assignee=agent_id,
            status="in-progress",
        )
        cache.put(updated)
        return _spec_detail(updated)

    @mcp.tool(
        description="Release a claimed spec. Clears assignee and sets status back to pending.",
    )
    def release_spec(
        spec_id: str,
        agent_id: str = "mcp-agent",
    ) -> dict:
        """Release a previously claimed spec."""
        ctx = create_context(specs_dir)
        spec = ctx.store.get(spec_id)

        if spec.meta.assignee and spec.meta.assignee != agent_id:
            raise ValueError(
                f"{spec_id} is claimed by {spec.meta.assignee!r}, not {agent_id!r}."
            )

        updated = ctx.store.update(
            spec_id,
            agent_id=agent_id,
            assignee="",
            status="pending",
        )
        cache.put(updated)
        return _spec_detail(updated)

    @mcp.tool(
        description="Search specs by text. Searches titles and body via FTS5.",
        annotations={"readOnlyHint": True},
    )
    def search_specs(
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """Full-text search across spec titles and body content."""
        _ensure_warm(cache, specs_dir)
        filters = SpecFilter(search=query)
        results = cache.query(filters=filters)
        return [_spec_summary(s) for s in results[:limit]]

    @mcp.tool(
        description="Validate all specs for schema violations, dependency cycles, "
        "and lifecycle inconsistencies.",
        annotations={"readOnlyHint": True},
    )
    def validate_specs() -> dict:
        """Run consistency checks and return issues found."""
        ctx = create_context(specs_dir)
        all_specs = ctx.refresh_graph()
        issues = ctx.lifecycle.validate_consistency(
            all_specs=all_specs,
            cycles=ctx.config.cycles,
        )
        cycles = ctx.graph.detect_cycles()

        return {
            "issues": [i.model_dump(mode="json") for i in issues],
            "dependency_cycles": cycles,
            "total_issues": len(issues) + len(cycles),
        }

    @mcp.tool(
        description="Export the full dependency graph as nodes and typed edges.",
        annotations={"readOnlyHint": True},
    )
    def get_dependency_graph() -> dict:
        """Get the spec dependency DAG for visualization or reasoning."""
        _ensure_warm(cache, specs_dir)
        ctx = create_context(specs_dir)
        all_specs = cache.query()
        ctx.graph.build(all_specs)
        return ctx.graph.to_dict()
