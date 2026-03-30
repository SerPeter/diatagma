"""Pydantic models for specs, frontmatter metadata, and configuration.

Defines the canonical shape of a spec — both the YAML frontmatter fields
and the parsed markdown body sections. Used by parser.py for
serialization and by schema.py for validation.

All spec types (story, epic, spike, bug, chore, docs) share the same
model structure. The ``type`` field distinguishes them; file extensions
(``.story.md``, ``.epic.md``, ``.spike.md``) provide visual identification.

Epics are specs too — they get their own ID, body, acceptance criteria,
and participate in the dependency graph. Child specs reference their
parent via the ``parent`` field using the parent's spec ID.

Key models:
    SpecMeta     — frontmatter fields (id, title, status, type, tags, parent, etc.)
    SpecBody     — parsed markdown sections (description, context, behavior, etc.)
    Spec         — SpecMeta + SpecBody + file path
    Settings     — loaded from .tasks/config/settings.yaml
    PrefixDef    — prefix definition from prefixes.yaml
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPEC_ID_PATTERN = r"^[A-Z]{1,5}-\d{3,}$"
"""Regex pattern for spec IDs: 1-5 uppercase letters, hyphen, 3+ digits."""

FIBONACCI_POINTS = (1, 2, 3, 5, 8, 13, 21)
"""Valid story point values (Fibonacci sequence)."""

DEFAULT_STATUSES = ("pending", "in-progress", "in-review", "done", "cancelled")
"""Default spec statuses. Configurable via settings.yaml."""

DEFAULT_TYPES = ("epic", "feature", "bug", "spike", "chore", "docs")
"""Default spec types. Configurable via settings.yaml."""

# ---------------------------------------------------------------------------
# Reusable annotated types
# ---------------------------------------------------------------------------

SpecId = Annotated[str, Field(pattern=SPEC_ID_PATTERN)]
"""A spec identifier matching the PREFIX-NNN pattern."""


class SpecLinks(BaseModel):
    """Typed relationships between specs.

    Declared on the affected spec only — inverse lookups are computed
    by the graph at query time.
    """

    blocked_by: list[SpecId] = Field(default_factory=list)
    relates_to: list[SpecId] = Field(default_factory=list)
    supersedes: list[SpecId] = Field(default_factory=list)
    discovered_from: SpecId | None = None

    model_config = ConfigDict(frozen=True)


# ---------------------------------------------------------------------------
# Spec data models
# ---------------------------------------------------------------------------


class SpecMeta(BaseModel):
    """YAML frontmatter fields — maps 1:1 to the metadata block in a spec file."""

    id: SpecId
    title: Annotated[str, Field(max_length=120)]
    status: str = "pending"
    type: str
    tags: list[str] = Field(default_factory=list)
    business_value: Annotated[int, Field(ge=-1000, le=1000)] | None = None
    story_points: Literal[1, 2, 3, 5, 8, 13, 21] | None = None
    sprint: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    links: SpecLinks = Field(default_factory=SpecLinks)
    parent: SpecId | None = None
    created: date
    updated: date | None = None


class SpecBody(BaseModel):
    """Parsed markdown body sections.

    Named fields cover the union of all template types (story, epic, spike).
    Unknown sections are preserved in ``extra_sections`` for round-tripping.
    """

    # Story sections
    description: str | None = None
    context: str | None = None
    behavior: str | None = None
    constraints: str | None = None
    verification: str | None = None
    references: str | None = None
    implementation_summary: str | None = None
    implementation_notes: str | None = None

    # Epic sections
    vision: str | None = None
    stories: str | None = None

    # Spike sections
    research_questions: str | None = None
    findings: str | None = None
    deliverables: str | None = None
    recommendation: str | None = None

    # Legacy / alternate names
    requirements: str | None = None
    acceptance_criteria: str | None = None
    implementation_details: str | None = None

    # Catch-all for unknown sections
    extra_sections: dict[str, str] = Field(default_factory=dict)


class Spec(BaseModel):
    """A complete spec: metadata + body + filesystem context + computed fields."""

    meta: SpecMeta
    body: SpecBody = Field(default_factory=SpecBody)
    file_path: Path | None = None
    raw_body: str | None = None

    # Set post-construction by priority and graph modules
    priority_score: float = 0.0
    is_blocked: bool = False


# ---------------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------------


class PrefixDef(BaseModel):
    """A prefix definition from prefixes.yaml."""

    description: str
    template: str = "story"


class DueDateUrgency(BaseModel):
    """Due-date urgency thresholds for priority scoring."""

    critical_days: int = 3
    warning_days: int = 7
    critical_bonus: float = 200.0
    warning_bonus: float = 50.0


class PriorityWeights(BaseModel):
    """WSJF-style priority weights including due-date urgency."""

    business_value: float = 1.0
    time_criticality: float = 0.5
    risk_reduction: float = 0.3
    unblocks_bonus: float = 50.0
    age_bonus_per_day: float = 0.5
    due_date_urgency: DueDateUrgency = Field(default_factory=DueDateUrgency)


class PriorityConfig(BaseModel):
    """Top-level priority scoring configuration (wraps weights)."""

    weights: PriorityWeights = Field(default_factory=PriorityWeights)


class Sprint(BaseModel):
    """A sprint boundary definition."""

    name: str
    start: date
    end: date
    goal: str = ""


class Settings(BaseModel):
    """Tool-level settings from settings.yaml."""

    default_assignee: str = ""
    statuses: list[str] = Field(
        default_factory=lambda: list(DEFAULT_STATUSES),
    )
    types: list[str] = Field(
        default_factory=lambda: list(DEFAULT_TYPES),
    )
    story_point_scale: list[int] = Field(
        default_factory=lambda: list(FIBONACCI_POINTS),
    )
    business_value_range: tuple[int, int] = (-1000, 1000)
    claim_timeout_minutes: int = 30
    web_port: int = 8742
    mcp_transport: str = "stdio"


class SchemaFieldConstraint(BaseModel):
    """A single field's validation rules from schema.yaml."""

    type: str
    pattern: str | None = None
    max_length: int | None = None
    min: int | None = None
    max: int | None = None
    values: list[int | str] | None = None
    item_type: str | None = None


class SchemaConfig(BaseModel):
    """Frontmatter schema validation rules from schema.yaml."""

    required_fields: list[str] = Field(default_factory=list)
    required_by_status: dict[str, list[str]] = Field(default_factory=dict)
    field_types: dict[str, SchemaFieldConstraint] = Field(default_factory=dict)


class HookCondition(BaseModel):
    """Condition that triggers a lifecycle hook."""

    model_config = ConfigDict(extra="allow")

    status: str | None = None


class HookEntry(BaseModel):
    """A single lifecycle hook entry."""

    when: HookCondition | None = None
    action: str


class HooksConfig(BaseModel):
    """Lifecycle hooks from hooks.yaml."""

    on_status_change: list[HookEntry] = Field(default_factory=list)
    on_create: list[HookEntry] = Field(default_factory=list)
    on_claim_timeout: list[HookEntry] = Field(default_factory=list)


class ChangelogEntry(BaseModel):
    """A single parsed changelog entry."""

    model_config = ConfigDict(frozen=True)

    date: date
    spec_id: str
    action: str
    field: str | None = None
    old: str | None = None
    new: str | None = None
    agent_id: str = "unknown"


# ---------------------------------------------------------------------------
# Query / filter types (used by store and cache)
# ---------------------------------------------------------------------------


class SpecFilter(BaseModel):
    """Filters for listing specs. All fields optional; None = no filter."""

    status: str | list[str] | None = None
    type: str | list[str] | None = None
    tags: list[str] | None = None
    prefix: str | None = None
    parent: str | None = None
    assignee: str | None = None
    sprint: str | None = None
    search: str | None = None

    model_config = ConfigDict(frozen=True)


class SortField(str, Enum):
    """Sort key for listing specs."""

    ID = "id"
    TITLE = "title"
    STATUS = "status"
    CREATED = "created"
    UPDATED = "updated"
    BUSINESS_VALUE = "business_value"
    STORY_POINTS = "story_points"
    PRIORITY = "priority"


__all__ = [
    "DEFAULT_STATUSES",
    "DEFAULT_TYPES",
    "FIBONACCI_POINTS",
    "SPEC_ID_PATTERN",
    "ChangelogEntry",
    "DueDateUrgency",
    "HookCondition",
    "HookEntry",
    "HooksConfig",
    "PrefixDef",
    "PriorityConfig",
    "PriorityWeights",
    "SchemaConfig",
    "SchemaFieldConstraint",
    "Settings",
    "SortField",
    "Spec",
    "SpecBody",
    "SpecFilter",
    "SpecId",
    "SpecLinks",
    "SpecMeta",
    "Sprint",
]
