"""Tests for parser.fill_body_sections — surgical section replacement."""

from diatagma.core.parser import fill_body_sections

_TEMPLATE = (
    "## Description\n\n<!-- one-liner -->\n\n"
    "## Context\n\n<!-- why -->\n\n"
    "## Verification\n\n- [ ] ...\n"
)


class TestFillBodySections:
    def test_fills_description(self):
        out = fill_body_sections(_TEMPLATE, {"description": "Users can do X"})
        assert "## Description\n\nUsers can do X" in out
        # Other sections preserved verbatim
        assert "<!-- why -->" in out
        assert "- [ ] ..." in out

    def test_fills_last_section(self):
        out = fill_body_sections(
            _TEMPLATE, {"verification": "- [ ] does A\n- [ ] does B"}
        )
        assert "## Verification\n\n- [ ] does A\n- [ ] does B" in out
        assert "<!-- one-liner -->" in out

    def test_fills_multiple(self):
        out = fill_body_sections(
            _TEMPLATE,
            {"description": "Desc here", "verification": "- [ ] crit"},
        )
        assert "Desc here" in out
        assert "- [ ] crit" in out

    def test_appends_missing_section(self):
        out = fill_body_sections("## Description\n\ntext\n", {"context": "ctx body"})
        assert "## Context\n\nctx body" in out
        assert "## Description\n\ntext" in out
