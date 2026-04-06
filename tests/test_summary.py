"""Tests for implementation summary field — parsing, rendering, and archive warning."""

from datetime import date
from pathlib import Path

import pytest
from loguru import logger

from diatagma.core.models import PrefixDef, Spec, SpecBody, SpecMeta
from diatagma.core.parser import (
    _parse_body,
    parse_spec_file,
    render_spec,
    write_spec_file,
)
from diatagma.core.store import SpecStore
from tests.conftest import seed_spec_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SPEC_WITH_SUMMARY = """\
---
id: DIA-001
title: Test spec with summary
type: feature
status: done
created: 2026-03-27
---

## Description

Build the widget system.

## Implementation Summary

Widget system built using factory pattern. Chose composition over inheritance
for extensibility. Cache invalidation handled via mtime checks.

## Implementation Notes

Used factory pattern for widget creation.
Decided against singleton — too rigid for testing.
"""

SPEC_WITHOUT_SUMMARY = """\
---
id: DIA-002
title: Test spec without summary
type: feature
status: done
created: 2026-03-27
---

## Description

Implement the parser.

## Implementation Notes

Chose python-frontmatter for YAML parsing.
"""


# ===========================================================================
# TestImplementationSummaryParsing
# ===========================================================================


class TestImplementationSummaryParsing:
    """Implementation Summary parses into spec.body.implementation_summary."""

    def test_parsed_into_field(self, tmp_path: Path):
        path = tmp_path / "DIA-001-test.story.md"
        path.write_text(SPEC_WITH_SUMMARY, encoding="utf-8")
        spec = parse_spec_file(path)

        assert spec.body.implementation_summary is not None
        assert "factory pattern" in spec.body.implementation_summary

    def test_not_in_extra_sections(self, tmp_path: Path):
        path = tmp_path / "DIA-001-test.story.md"
        path.write_text(SPEC_WITH_SUMMARY, encoding="utf-8")
        spec = parse_spec_file(path)

        assert "Implementation Summary" not in spec.body.extra_sections

    def test_no_summary_field_is_none(self, tmp_path: Path):
        path = tmp_path / "DIA-002-test.story.md"
        path.write_text(SPEC_WITHOUT_SUMMARY, encoding="utf-8")
        spec = parse_spec_file(path)

        assert spec.body.implementation_summary is None

    def test_body_parse_section(self):
        body_text = (
            "## Implementation Summary\n\nThis is the summary."
            "\n\n## Description\n\nDetails."
        )
        body = _parse_body(body_text)
        assert body.implementation_summary == "This is the summary."
        assert body.description == "Details."

    def test_empty_section(self):
        body_text = "## Implementation Summary\n\n## Description\n\nDetails."
        body = _parse_body(body_text)
        assert body.implementation_summary is None
        assert body.description == "Details."


# ===========================================================================
# TestImplementationSummaryRenderOrder
# ===========================================================================


class TestImplementationSummaryRenderOrder:
    """Implementation Summary renders above Implementation Notes in output."""

    def test_before_implementation_notes(self):
        spec = Spec(
            meta=SpecMeta(
                id="DIA-001",
                title="Test",
                type="feature",
                created=date(2026, 3, 27),
            ),
            body=SpecBody(
                description="Build widgets.",
                implementation_summary="Built widgets using factory pattern.",
                implementation_notes="Used factory pattern.",
            ),
        )
        rendered = render_spec(spec)
        summary_pos = rendered.index("## Implementation Summary")
        notes_pos = rendered.index("## Implementation Notes")
        assert summary_pos < notes_pos

    def test_after_references(self):
        spec = Spec(
            meta=SpecMeta(
                id="DIA-001",
                title="Test",
                type="feature",
                created=date(2026, 3, 27),
            ),
            body=SpecBody(
                references="See ADR-001.",
                implementation_summary="Summary content.",
            ),
        )
        rendered = render_spec(spec)
        refs_pos = rendered.index("## References")
        summary_pos = rendered.index("## Implementation Summary")
        assert refs_pos < summary_pos

    def test_render_without_summary_unchanged(self):
        """Specs without summary render normally — no empty section."""
        spec = Spec(
            meta=SpecMeta(
                id="DIA-001",
                title="Test",
                type="feature",
                created=date(2026, 3, 27),
            ),
            body=SpecBody(
                description="Build widgets.",
                implementation_notes="Used factory pattern.",
            ),
        )
        rendered = render_spec(spec)
        assert "## Implementation Summary" not in rendered

    def test_round_trip_preserves_summary(self, tmp_path: Path):
        """Write spec with summary, parse it back, summary intact."""
        spec = Spec(
            meta=SpecMeta(
                id="DIA-001",
                title="Round trip",
                type="feature",
                created=date(2026, 3, 27),
            ),
            body=SpecBody(
                description="Build widgets.",
                implementation_summary="Built using factory pattern.",
                implementation_notes="Factory pattern chosen.",
            ),
        )
        path = tmp_path / "DIA-001-round-trip.story.md"
        write_spec_file(spec, path)
        parsed = parse_spec_file(path)

        assert parsed.body.implementation_summary == "Built using factory pattern."
        assert parsed.body.implementation_notes == "Factory pattern chosen."
        assert parsed.body.description == "Build widgets."


# ===========================================================================
# TestArchiveWarning
# ===========================================================================


class TestArchiveWarning:
    """move_to_archive warns when implementation summary is missing."""

    @pytest.fixture
    def prefixes(self) -> dict[str, PrefixDef]:
        return {"DIA": PrefixDef(description="test", template="story")}

    @pytest.fixture
    def store(self, tmp_specs_dir, prefixes) -> SpecStore:
        return SpecStore(tmp_specs_dir, prefixes, templates={"story": ""})

    def test_archive_without_summary_warns(self, store: SpecStore, tmp_specs_dir: Path):
        seed_spec_file(tmp_specs_dir, "DIA-001", "No summary")
        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(str(m)), level="WARNING")
        try:
            spec = store.move_to_archive("DIA-001")
        finally:
            logger.remove(sink_id)

        assert spec.file_path is not None
        assert "archive" in str(spec.file_path)
        assert any(
            "without an ## Implementation Summary section" in m for m in messages
        )

    def test_archive_with_summary_no_warning(
        self, store: SpecStore, tmp_specs_dir: Path
    ):
        meta = SpecMeta.model_validate(
            {
                "id": "DIA-002",
                "title": "Has summary",
                "type": "feature",
                "status": "done",
                "created": date(2026, 3, 27),
            }
        )
        spec = Spec(
            meta=meta,
            body=SpecBody(
                description="Build widgets.",
                implementation_summary="Built widgets with factory pattern.",
            ),
            file_path=tmp_specs_dir / "DIA-002-has-summary.story.md",
        )
        assert spec.file_path is not None
        write_spec_file(spec, spec.file_path)

        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(str(m)), level="WARNING")
        try:
            archived = store.move_to_archive("DIA-002")
        finally:
            logger.remove(sink_id)

        assert archived.file_path is not None
        assert "archive" in str(archived.file_path)
        assert not any(
            "without an ## Implementation Summary section" in m for m in messages
        )

    def test_archive_succeeds_regardless(self, store: SpecStore, tmp_specs_dir: Path):
        """Archive proceeds even without summary — warning only, not blocking."""
        seed_spec_file(tmp_specs_dir, "DIA-003", "No summary either")
        spec = store.move_to_archive("DIA-003")
        assert spec.file_path is not None
        assert (tmp_specs_dir / "archive").glob("DIA-003-*.md")
