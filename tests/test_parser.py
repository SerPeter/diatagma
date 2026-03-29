"""Tests for core.parser — spec file round-tripping (markdown + YAML frontmatter)."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from diatagma.core.models import Spec, SpecBody, SpecMeta
from diatagma.core.parser import (
    ParseError,
    _field_to_heading,
    _heading_to_field,
    _parse_body,
    parse_frontmatter,
    parse_spec_file,
    render_spec,
    write_spec_file,
)
from tests.conftest import (
    EPIC_SPEC_TEXT,
    MINIMAL_SPEC_TEXT,
    SAMPLE_SPEC_TEXT,
    SPEC_WITH_EXTRAS_TEXT,
    SPIKE_SPEC_TEXT,
)


# ===========================================================================
# Heading ↔ field name conversion
# ===========================================================================


class TestHeadingConversion:
    """Heading to field name and back."""

    @pytest.mark.parametrize(
        ("heading", "field"),
        [
            ("Description", "description"),
            ("Context", "context"),
            ("Implementation Notes", "implementation_notes"),
            ("Research Questions", "research_questions"),
            ("Acceptance Criteria", "acceptance_criteria"),
        ],
    )
    def test_heading_to_field(self, heading: str, field: str):
        assert _heading_to_field(heading) == field

    @pytest.mark.parametrize(
        ("field", "heading"),
        [
            ("description", "Description"),
            ("implementation_notes", "Implementation Notes"),
            ("research_questions", "Research Questions"),
        ],
    )
    def test_field_to_heading(self, field: str, heading: str):
        assert _field_to_heading(field) == heading


# ===========================================================================
# Body parsing
# ===========================================================================


class TestParseBody:
    """Internal body parsing from markdown sections."""

    def test_empty_content(self):
        body = _parse_body("")
        assert body.description is None
        assert body.extra_sections == {}

    def test_whitespace_only(self):
        body = _parse_body("   \n\n  ")
        assert body.description is None

    def test_single_section(self):
        body = _parse_body("## Description\n\nHello world.")
        assert body.description == "Hello world."
        assert body.context is None

    def test_multiple_sections(self):
        text = "## Description\n\nDesc text.\n\n## Context\n\nCtx text."
        body = _parse_body(text)
        assert body.description == "DESC text." or body.description == "Desc text."
        assert body.description == "Desc text."
        assert body.context == "Ctx text."

    def test_empty_section_becomes_none(self):
        text = "## Description\n\n## Context\n\nSome context."
        body = _parse_body(text)
        assert body.description is None
        assert body.context == "Some context."

    def test_unknown_section_goes_to_extras(self):
        text = "## Description\n\nDesc.\n\n## My Custom\n\nCustom content."
        body = _parse_body(text)
        assert body.description == "Desc."
        assert "My Custom" in body.extra_sections
        assert body.extra_sections["My Custom"] == "Custom content."

    def test_nested_h3_preserved(self):
        text = (
            "## Behavior\n\n"
            "### Scenario: Login\n\n"
            "- **Given** a user\n"
            "- **When** they log in\n"
            "- **Then** success"
        )
        body = _parse_body(text)
        assert body.behavior is not None
        assert "### Scenario: Login" in body.behavior
        assert "**Given** a user" in body.behavior

    def test_code_block_preserved(self):
        text = "## Description\n\n```python\ndef foo():\n    pass\n```"
        body = _parse_body(text)
        assert body.description is not None
        assert "```python" in body.description
        assert "def foo():" in body.description

    def test_all_story_sections(self):
        text = (
            "## Description\n\nD\n\n"
            "## Context\n\nC\n\n"
            "## Behavior\n\nB\n\n"
            "## Constraints\n\nCo\n\n"
            "## Verification\n\nV\n\n"
            "## References\n\nR\n\n"
            "## Implementation Notes\n\nIN"
        )
        body = _parse_body(text)
        assert body.description == "D"
        assert body.context == "C"
        assert body.behavior == "B"
        assert body.constraints == "Co"
        assert body.verification == "V"
        assert body.references == "R"
        assert body.implementation_notes == "IN"

    def test_epic_sections(self):
        text = "## Vision\n\nV\n\n## Stories\n\n- Story 1\n- Story 2"
        body = _parse_body(text)
        assert body.vision == "V"
        assert body.stories is not None
        assert "Story 1" in body.stories

    def test_spike_sections(self):
        text = (
            "## Research Questions\n\n1. Q1\n\n"
            "## Findings\n\nF\n\n"
            "## Recommendation\n\nR"
        )
        body = _parse_body(text)
        assert body.research_questions == "1. Q1"
        assert body.findings == "F"
        assert body.recommendation == "R"


# ===========================================================================
# parse_frontmatter
# ===========================================================================


class TestParseFrontmatter:
    """Extract metadata from text without body parsing."""

    def test_basic(self, sample_spec_text: str):
        meta = parse_frontmatter(sample_spec_text)
        assert meta.id == "DIA-001"
        assert meta.title == "Define Pydantic models"
        assert meta.status == "pending"
        assert meta.type == "feature"
        assert meta.tags == ["core", "models"]
        assert meta.business_value == 500
        assert meta.story_points == 5
        assert meta.parent == "DIA-011"

    def test_date_coercion(self, sample_spec_text: str):
        meta = parse_frontmatter(sample_spec_text)
        assert meta.created == date(2026, 3, 27)

    def test_minimal(self, minimal_spec_text: str):
        meta = parse_frontmatter(minimal_spec_text)
        assert meta.id == "DIA-099"
        assert meta.status == "pending"  # default

    def test_malformed_yaml(self):
        text = "---\n: invalid: yaml: {{{\n---\nBody."
        with pytest.raises(ParseError, match="malformed YAML"):
            parse_frontmatter(text)

    def test_missing_required_fields(self):
        text = "---\ntitle: No ID\n---\nBody."
        with pytest.raises(ValidationError):
            parse_frontmatter(text)


# ===========================================================================
# parse_spec_file
# ===========================================================================


class TestParseSpecFile:
    """Read spec files from disk."""

    def test_full_story(self, tmp_path: Path):
        f = tmp_path / "DIA-001.story.md"
        f.write_text(SAMPLE_SPEC_TEXT, encoding="utf-8")
        spec = parse_spec_file(f)
        assert spec.meta.id == "DIA-001"
        assert spec.body.description is not None
        assert "canonical Pydantic models" in spec.body.description
        assert spec.file_path == f
        assert spec.raw_body is not None

    def test_minimal_no_body(self, tmp_path: Path):
        f = tmp_path / "DIA-099.story.md"
        f.write_text(MINIMAL_SPEC_TEXT, encoding="utf-8")
        spec = parse_spec_file(f)
        assert spec.meta.id == "DIA-099"
        assert spec.body.description is None
        assert spec.raw_body is None  # empty content → None

    def test_with_extra_sections(self, tmp_path: Path):
        f = tmp_path / "DIA-050.spike.md"
        f.write_text(SPEC_WITH_EXTRAS_TEXT, encoding="utf-8")
        spec = parse_spec_file(f)
        assert spec.meta.id == "DIA-050"
        assert spec.body.description is not None
        assert spec.body.research_questions is not None
        assert "My Custom Section" in spec.body.extra_sections
        assert "Another Extra" in spec.body.extra_sections

    def test_epic(self, tmp_path: Path):
        f = tmp_path / "DIA-011.epic.md"
        f.write_text(EPIC_SPEC_TEXT, encoding="utf-8")
        spec = parse_spec_file(f)
        assert spec.meta.type == "epic"
        assert spec.body.vision is not None
        assert spec.body.stories is not None

    def test_nested_h3_preserved(self, tmp_path: Path):
        f = tmp_path / "DIA-001.story.md"
        f.write_text(SAMPLE_SPEC_TEXT, encoding="utf-8")
        spec = parse_spec_file(f)
        assert spec.body.behavior is not None
        assert "### Scenario:" in spec.body.behavior

    def test_file_not_found(self):
        with pytest.raises(OSError):
            parse_spec_file(Path("/nonexistent/DIA-999.md"))

    def test_malformed_yaml_file(self, tmp_path: Path):
        f = tmp_path / "bad.md"
        f.write_text("---\n: {{invalid\n---\nBody", encoding="utf-8")
        with pytest.raises(ParseError, match="malformed YAML"):
            parse_spec_file(f)

    def test_real_spec_file(self):
        """Parse an actual spec file from the repo's .tasks/ directory."""
        real = (
            Path(__file__).resolve().parent.parent
            / ".tasks"
            / "DIA-001-pydantic-models.story.md"
        )
        if not real.exists():
            pytest.skip("Real spec file not available")
        spec = parse_spec_file(real)
        assert spec.meta.id == "DIA-001"
        assert spec.meta.type == "feature"


# ===========================================================================
# render_spec
# ===========================================================================


class TestRenderSpec:
    """Render Spec back to markdown string."""

    def test_uses_raw_body_when_set(self):
        raw = "## Description\n\nOriginal formatting preserved."
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
            raw_body=raw,
        )
        rendered = render_spec(spec)
        assert "Original formatting preserved." in rendered
        assert rendered.startswith("---\n")

    def test_renders_from_body_fields(self):
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
            body=SpecBody(description="Desc text.", context="Ctx text."),
        )
        rendered = render_spec(spec)
        assert "## Description" in rendered
        assert "Desc text." in rendered
        assert "## Context" in rendered
        assert "Ctx text." in rendered

    def test_excludes_none_fields_from_frontmatter(self):
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
        )
        rendered = render_spec(spec)
        assert "business_value" not in rendered
        assert "due_date" not in rendered
        assert "assignee" not in rendered

    def test_renders_extra_sections(self):
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
            body=SpecBody(
                description="Desc.",
                extra_sections={"My Custom": "Custom content."},
            ),
        )
        rendered = render_spec(spec)
        assert "## My Custom" in rendered
        assert "Custom content." in rendered

    def test_skips_none_body_fields(self):
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
            body=SpecBody(description="Only desc."),
        )
        rendered = render_spec(spec)
        assert "## Description" in rendered
        assert "## Context" not in rendered
        assert "## Behavior" not in rendered

    def test_ends_with_newline(self):
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
        )
        rendered = render_spec(spec)
        assert rendered.endswith("\n")


# ===========================================================================
# write_spec_file
# ===========================================================================


class TestWriteSpecFile:
    """Write spec to disk."""

    def test_write_and_read_back(self, tmp_path: Path):
        spec = Spec(
            meta=SpecMeta.model_validate(
                {
                    "id": "DIA-001",
                    "title": "Test write",
                    "type": "feature",
                    "created": date(2026, 3, 27),
                }
            ),
            body=SpecBody(description="Written to disk."),
        )
        f = tmp_path / "DIA-001.story.md"
        write_spec_file(spec, f)

        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "DIA-001" in content
        assert "## Description" in content
        assert "Written to disk." in content


# ===========================================================================
# Round-trip tests
# ===========================================================================


class TestRoundTrip:
    """Parse → render → parse produces identical Spec."""

    def _assert_round_trip(self, text: str, tmp_path: Path, filename: str):
        """Write text to file, parse, render, parse again, compare."""
        f = tmp_path / filename
        f.write_text(text, encoding="utf-8")

        spec1 = parse_spec_file(f)
        rendered = render_spec(spec1)

        # Write rendered and parse again
        f2 = tmp_path / f"rt_{filename}"
        f2.write_text(rendered, encoding="utf-8")
        spec2 = parse_spec_file(f2)

        # Metadata must be identical
        assert spec1.meta == spec2.meta
        # Body sections must be identical
        assert spec1.body == spec2.body

    def test_story_round_trip(self, tmp_path: Path):
        self._assert_round_trip(SAMPLE_SPEC_TEXT, tmp_path, "story.md")

    def test_epic_round_trip(self, tmp_path: Path):
        self._assert_round_trip(EPIC_SPEC_TEXT, tmp_path, "epic.md")

    def test_spike_round_trip(self, tmp_path: Path):
        self._assert_round_trip(SPIKE_SPEC_TEXT, tmp_path, "spike.md")

    def test_minimal_round_trip(self, tmp_path: Path):
        self._assert_round_trip(MINIMAL_SPEC_TEXT, tmp_path, "minimal.md")

    def test_extras_round_trip(self, tmp_path: Path):
        self._assert_round_trip(SPEC_WITH_EXTRAS_TEXT, tmp_path, "extras.md")
