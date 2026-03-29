"""Tests for core.models — Pydantic model validation and defaults."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from diatagma.core.models import (
    DEFAULT_STATUSES,
    DEFAULT_TYPES,
    FIBONACCI_POINTS,
    DueDateUrgency,
    HookCondition,
    HookEntry,
    HooksConfig,
    PrefixDef,
    PriorityConfig,
    SchemaConfig,
    Settings,
    Spec,
    SpecBody,
    SpecLinks,
    SpecMeta,
    Sprint,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_META = {
    "id": "DIA-001",
    "title": "Test spec",
    "type": "feature",
    "created": date(2026, 3, 27),
}


def _meta(**overrides: object) -> SpecMeta:
    """Build a SpecMeta with minimal required fields + overrides."""
    return SpecMeta.model_validate({**MINIMAL_META, **overrides})


# ===========================================================================
# SpecMeta
# ===========================================================================


class TestSpecMeta:
    """SpecMeta validation and defaults."""

    def test_minimal_construction(self):
        m = _meta()
        assert m.id == "DIA-001"
        assert m.title == "Test spec"
        assert m.status == "pending"
        assert m.type == "feature"
        assert m.tags == []
        assert m.business_value is None
        assert m.story_points is None
        assert m.links == SpecLinks()
        assert m.parent is None
        assert m.updated is None

    def test_full_construction(self):
        m = SpecMeta(
            id="CORE-042",
            title="Full spec",
            status="in-progress",
            type="bug",
            tags=["backend", "urgent"],
            business_value=500,
            story_points=8,
            sprint="Sprint 1",
            assignee="alice",
            due_date=date(2026, 4, 15),
            links=SpecLinks(
                blocked_by=["CORE-001", "CORE-002", "CORE-010"],
                relates_to=["EX-005"],
            ),
            parent="CORE-040",
            created=date(2026, 3, 27),
            updated=date(2026, 3, 28),
        )
        assert m.tags == ["backend", "urgent"]
        assert m.business_value == 500
        assert m.story_points == 8
        assert m.links.blocked_by == ["CORE-001", "CORE-002", "CORE-010"]
        assert m.links.relates_to == ["EX-005"]
        assert m.parent == "CORE-040"

    # --- ID validation ---

    @pytest.mark.parametrize(
        "valid_id",
        ["A-001", "AB-999", "ABCDE-99999", "DIA-001", "X-1000"],
    )
    def test_valid_id_formats(self, valid_id: str):
        m = _meta(id=valid_id)
        assert m.id == valid_id

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "abc-001",  # lowercase
            "ABCDEF-001",  # 6 letters
            "AB-01",  # only 2 digits
            "AB001",  # no hyphen
            "-001",  # no prefix
            "AB-",  # no number
            "",  # empty
        ],
    )
    def test_invalid_id_formats(self, invalid_id: str):
        with pytest.raises(ValidationError):
            _meta(id=invalid_id)

    # --- Title ---

    def test_title_max_length(self):
        m = _meta(title="x" * 120)
        assert len(m.title) == 120

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            _meta(title="x" * 121)

    # --- Status / Type are plain strings ---

    def test_status_accepts_any_string(self):
        m = _meta(status="custom-status")
        assert m.status == "custom-status"

    def test_type_accepts_any_string(self):
        m = _meta(type="custom-type")
        assert m.type == "custom-type"

    # --- Business value ---

    @pytest.mark.parametrize("bv", [-1000, 0, 500, 1000])
    def test_valid_business_value(self, bv: int):
        m = _meta(business_value=bv)
        assert m.business_value == bv

    @pytest.mark.parametrize("bv", [-1001, 1001])
    def test_invalid_business_value(self, bv: int):
        with pytest.raises(ValidationError):
            _meta(business_value=bv)

    # --- Story points ---

    @pytest.mark.parametrize("sp", FIBONACCI_POINTS)
    def test_valid_story_points(self, sp: int):
        m = _meta(story_points=sp)
        assert m.story_points == sp

    @pytest.mark.parametrize("sp", [0, 4, 6, 10, -1])
    def test_invalid_story_points(self, sp: int):
        with pytest.raises(ValidationError):
            _meta(story_points=sp)

    # --- Links validation ---

    def test_valid_links(self):
        m = _meta(links={"blocked_by": ["AB-001", "CDE-999"], "relates_to": ["EX-005"]})
        assert m.links.blocked_by == ["AB-001", "CDE-999"]
        assert m.links.relates_to == ["EX-005"]

    def test_invalid_blocked_by_id(self):
        with pytest.raises(ValidationError):
            _meta(links={"blocked_by": ["not-an-id"]})

    def test_invalid_relates_to_id(self):
        with pytest.raises(ValidationError):
            _meta(links={"relates_to": [""]})

    def test_invalid_supersedes_id(self):
        with pytest.raises(ValidationError):
            _meta(links={"supersedes": ["lowercase-001"]})

    def test_valid_discovered_from(self):
        m = _meta(links={"discovered_from": "DIA-011"})
        assert m.links.discovered_from == "DIA-011"

    def test_invalid_discovered_from(self):
        with pytest.raises(ValidationError):
            _meta(links={"discovered_from": "bad"})

    # --- Parent validation ---

    def test_valid_parent(self):
        m = _meta(parent="DIA-011")
        assert m.parent == "DIA-011"

    def test_invalid_parent(self):
        with pytest.raises(ValidationError):
            _meta(parent="bad")

    # --- Required fields ---

    def test_missing_id(self):
        with pytest.raises(ValidationError):
            SpecMeta.model_validate(
                {"title": "x", "type": "feature", "created": date(2026, 1, 1)}
            )

    def test_missing_title(self):
        with pytest.raises(ValidationError):
            SpecMeta.model_validate(
                {"id": "A-001", "type": "feature", "created": date(2026, 1, 1)}
            )

    def test_missing_type(self):
        with pytest.raises(ValidationError):
            SpecMeta.model_validate(
                {"id": "A-001", "title": "x", "created": date(2026, 1, 1)}
            )

    def test_missing_created(self):
        with pytest.raises(ValidationError):
            SpecMeta.model_validate({"id": "A-001", "title": "x", "type": "feature"})

    # --- Date coercion ---

    def test_date_from_string(self):
        m = _meta(created="2026-03-27", due_date="2026-04-15")
        assert m.created == date(2026, 3, 27)
        assert m.due_date == date(2026, 4, 15)


# ===========================================================================
# SpecBody
# ===========================================================================


class TestSpecBody:
    """SpecBody defaults and population."""

    def test_default_construction(self):
        b = SpecBody()
        assert b.description is None
        assert b.context is None
        assert b.behavior is None
        assert b.vision is None
        assert b.research_questions is None
        assert b.extra_sections == {}

    def test_partial_population(self):
        b = SpecBody(description="A thing", context="Why it matters")
        assert b.description == "A thing"
        assert b.context == "Why it matters"
        assert b.behavior is None

    def test_extra_sections(self):
        b = SpecBody(extra_sections={"custom": "Custom content"})
        assert b.extra_sections["custom"] == "Custom content"


# ===========================================================================
# Spec
# ===========================================================================


class TestSpec:
    """Spec composite model."""

    def test_composition(self):
        meta = _meta()
        body = SpecBody(description="Hello")
        spec = Spec(meta=meta, body=body)
        assert spec.meta.id == "DIA-001"
        assert spec.body.description == "Hello"

    def test_defaults(self):
        spec = Spec(meta=_meta())
        assert spec.body.description is None
        assert spec.file_path is None
        assert spec.raw_body is None
        assert spec.priority_score == 0.0
        assert spec.is_blocked is False

    def test_computed_fields_mutable(self):
        spec = Spec(meta=_meta())
        spec.priority_score = 42.5
        spec.is_blocked = True
        assert spec.priority_score == 42.5
        assert spec.is_blocked is True

    def test_file_path(self):
        spec = Spec(meta=_meta(), file_path=Path("/tmp/DIA-001-test.story.md"))
        assert spec.file_path == Path("/tmp/DIA-001-test.story.md")

    def test_raw_body_preserved(self):
        raw = "## Description\n\nSome content"
        spec = Spec(meta=_meta(), raw_body=raw)
        assert spec.raw_body == raw


# ===========================================================================
# Configuration models
# ===========================================================================


class TestSettings:
    """Settings defaults and overrides."""

    def test_defaults(self):
        s = Settings()
        assert s.statuses == list(DEFAULT_STATUSES)
        assert s.types == list(DEFAULT_TYPES)
        assert s.story_point_scale == list(FIBONACCI_POINTS)
        assert s.business_value_range == (-1000, 1000)
        assert s.claim_timeout_minutes == 30
        assert s.web_port == 8742
        assert s.mcp_transport == "stdio"

    def test_custom_statuses(self):
        s = Settings(statuses=["open", "closed"])
        assert s.statuses == ["open", "closed"]

    def test_custom_types(self):
        s = Settings(types=["feature", "task"])
        assert s.types == ["feature", "task"]

    def test_from_yaml_dict(self):
        """Simulate loading from YAML (list coerced to tuple for bv range)."""
        d = {
            "default_assignee": "",
            "statuses": ["pending", "done"],
            "types": ["feature"],
            "story_point_scale": [1, 2, 3],
            "business_value_range": [-500, 500],
            "claim_timeout_minutes": 60,
            "web_port": 9000,
            "mcp_transport": "sse",
        }
        s = Settings.model_validate(d)
        assert s.business_value_range == (-500, 500)
        assert s.mcp_transport == "sse"


class TestPrefixDef:
    def test_basic(self):
        p = PrefixDef(description="Core services")
        assert p.template == "story"

    def test_custom_template(self):
        p = PrefixDef(description="Research", template="spike")
        assert p.template == "spike"


class TestPriorityConfig:
    def test_defaults(self):
        pc = PriorityConfig()
        assert pc.weights.business_value == 1.0
        assert pc.weights.time_criticality == 0.5
        assert pc.weights.risk_reduction == 0.3
        assert pc.weights.unblocks_bonus == 50.0
        assert pc.weights.age_bonus_per_day == 0.5
        assert pc.weights.due_date_urgency.critical_days == 3

    def test_from_yaml_dict(self):
        """Simulate nested YAML structure."""
        d = {
            "weights": {
                "business_value": 2.0,
                "time_criticality": 1.0,
                "risk_reduction": 0.5,
                "unblocks_bonus": 100.0,
                "age_bonus_per_day": 1.0,
                "due_date_urgency": {
                    "critical_days": 5,
                    "warning_days": 14,
                    "critical_bonus": 300.0,
                    "warning_bonus": 100.0,
                },
            },
        }
        pc = PriorityConfig.model_validate(d)
        assert pc.weights.business_value == 2.0
        assert pc.weights.due_date_urgency.critical_days == 5


class TestDueDateUrgency:
    def test_defaults(self):
        u = DueDateUrgency()
        assert u.critical_days == 3
        assert u.warning_days == 7
        assert u.critical_bonus == 200.0
        assert u.warning_bonus == 50.0


class TestSprint:
    def test_construction(self):
        s = Sprint(name="Sprint 1", start=date(2026, 3, 24), end=date(2026, 4, 7))
        assert s.goal == ""

    def test_with_goal(self):
        s = Sprint(
            name="Sprint 1",
            start=date(2026, 3, 24),
            end=date(2026, 4, 7),
            goal="Core models",
        )
        assert s.goal == "Core models"


class TestSchemaConfig:
    def test_empty(self):
        sc = SchemaConfig()
        assert sc.required_fields == []
        assert sc.required_by_status == {}
        assert sc.field_types == {}

    def test_from_yaml_dict(self):
        d = {
            "required_fields": ["id", "title", "status"],
            "required_by_status": {"in-progress": ["assignee"]},
            "field_types": {
                "id": {"type": "string", "pattern": r"^[A-Z]{1,5}-\d{3,}$"},
                "title": {"type": "string", "max_length": 120},
                "business_value": {"type": "integer", "min": -1000, "max": 1000},
                "story_points": {"type": "enum", "values": [1, 2, 3, 5, 8, 13, 21]},
            },
        }
        sc = SchemaConfig.model_validate(d)
        assert sc.required_fields == ["id", "title", "status"]
        assert sc.field_types["id"].pattern == r"^[A-Z]{1,5}-\d{3,}$"
        assert sc.field_types["business_value"].min == -1000
        assert sc.field_types["story_points"].values == [1, 2, 3, 5, 8, 13, 21]


class TestHooksConfig:
    def test_empty(self):
        hc = HooksConfig()
        assert hc.on_status_change == []
        assert hc.on_create == []
        assert hc.on_claim_timeout == []

    def test_with_entries(self):
        hc = HooksConfig(
            on_status_change=[
                HookEntry(
                    when=HookCondition(status="done"),
                    action="move_to_archive",
                ),
            ],
            on_create=[HookEntry(action="validate_frontmatter")],
        )
        assert len(hc.on_status_change) == 1
        assert hc.on_status_change[0].when is not None
        assert hc.on_status_change[0].when.status == "done"
        assert hc.on_status_change[0].action == "move_to_archive"
        assert hc.on_create[0].when is None
