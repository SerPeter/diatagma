"""Read and write spec files (markdown with YAML frontmatter).

Handles the serialization boundary: converts between on-disk spec
files and in-memory Spec/SpecMeta models. Uses python-frontmatter for
parsing and PyYAML for YAML round-tripping.

Key functions:
    parse_spec_file(path)  → Spec
    write_spec_file(spec, path)
    parse_frontmatter(text) → SpecMeta
    render_spec(spec) → str
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from diatagma.core.models import Spec, SpecBody, SpecMeta

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ParseError(Exception):
    """Raised when a spec file cannot be parsed (malformed YAML, encoding issues)."""

    def __init__(self, path: Path | str, reason: str) -> None:
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"{path}: {reason}")


# ---------------------------------------------------------------------------
# Heading ↔ field-name conversion
# ---------------------------------------------------------------------------

_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
"""Matches H2 headings in markdown."""

_KNOWN_FIELDS = frozenset(
    name for name in SpecBody.model_fields if name != "extra_sections"
)
"""SpecBody field names (excluding extra_sections)."""


def _heading_to_field(heading: str) -> str:
    """Convert an H2 heading to a SpecBody field name.

    ``"Implementation Notes"`` → ``"implementation_notes"``
    """
    return re.sub(r"[^\w\s]", "", heading).strip().lower().replace(" ", "_")


def _field_to_heading(field: str) -> str:
    """Convert a SpecBody field name to an H2 heading.

    ``"implementation_notes"`` → ``"Implementation Notes"``
    """
    return field.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Body parsing / rendering
# ---------------------------------------------------------------------------


def _parse_body(content: str) -> SpecBody:
    """Split markdown body on H2 headings into a SpecBody."""
    if not content or not content.strip():
        return SpecBody()

    fields: dict[str, Any] = {}
    extra: dict[str, str] = {}

    # Find all H2 heading positions
    matches = list(_H2_RE.finditer(content))

    for i, match in enumerate(matches):
        heading_text = match.group(1).strip()
        # Content starts after the heading line
        start = match.end()
        # Content ends at the next heading or EOF
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        raw_section = content[start:end].strip()
        field_name = _heading_to_field(heading_text)

        if field_name in _KNOWN_FIELDS:
            fields[field_name] = raw_section if raw_section else None
        else:
            if raw_section:
                extra[heading_text] = raw_section

    if extra:
        fields["extra_sections"] = extra

    return SpecBody.model_validate(fields)


def _render_body(body: SpecBody) -> str:
    """Render a SpecBody to markdown sections."""
    parts: list[str] = []

    for field_name in SpecBody.model_fields:
        if field_name == "extra_sections":
            continue
        value = getattr(body, field_name)
        if value is None:
            continue
        heading = _field_to_heading(field_name)
        parts.append(f"## {heading}\n\n{value}")

    for heading, content in body.extra_sections.items():
        parts.append(f"## {heading}\n\n{content}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Metadata serialization
# ---------------------------------------------------------------------------


def _meta_to_dict(meta: SpecMeta) -> dict[str, Any]:
    """Convert SpecMeta to a dict suitable for YAML frontmatter.

    Excludes None values and converts dates to ISO strings.
    """
    raw = meta.model_dump()
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None:
            continue
        # Skip empty lists/dicts
        if isinstance(value, (list, dict)) and not value:
            continue
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_spec_file(path: Path) -> Spec:
    """Read a spec file from disk and return a fully populated Spec."""
    path = Path(path)
    try:
        post = frontmatter.load(str(path))
    except yaml.YAMLError as exc:
        raise ParseError(path, f"malformed YAML frontmatter: {exc}") from exc
    except OSError:
        raise

    meta = SpecMeta.model_validate(post.metadata)
    body = _parse_body(post.content)

    return Spec(
        meta=meta,
        body=body,
        file_path=path,
        raw_body=post.content if post.content else None,
    )


def write_spec_file(spec: Spec, path: Path) -> None:
    """Serialize a Spec and write it to disk."""
    text = render_spec(spec)
    Path(path).write_text(text, encoding="utf-8")


def parse_frontmatter(text: str) -> SpecMeta:
    """Extract just the metadata from a spec text without full body parsing."""
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        raise ParseError("<string>", f"malformed YAML frontmatter: {exc}") from exc

    return SpecMeta.model_validate(post.metadata)


def render_spec(spec: Spec) -> str:
    """Render a Spec to a complete markdown string with YAML frontmatter."""
    meta_dict = _meta_to_dict(spec.meta)

    # Use raw_body for lossless round-trip when available
    if spec.raw_body is not None:
        body_text = spec.raw_body
    else:
        body_text = _render_body(spec.body)

    post = frontmatter.Post(body_text, **meta_dict)
    return frontmatter.dumps(post) + "\n"


__all__ = [
    "ParseError",
    "parse_frontmatter",
    "parse_spec_file",
    "render_spec",
    "write_spec_file",
]
