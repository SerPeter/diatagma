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
import frontmatter.default_handlers
import yaml
from yaml import SafeDumper

from diatagma.core.models import Spec, SpecBody, SpecMeta


# ---------------------------------------------------------------------------
# Custom YAML handler — preserves flow-style lists and key order
# ---------------------------------------------------------------------------


class _FlowListDumper(SafeDumper):
    """SafeDumper that uses flow style for short, simple lists."""


def _flow_list_representer(
    dumper: SafeDumper, data: list,  # type: ignore[type-arg]
) -> yaml.Node:
    """Represent lists of scalars in flow style [a, b, c]."""
    if all(isinstance(item, (str, int, float, bool)) for item in data):
        return dumper.represent_sequence(
            "tag:yaml.org,2002:seq", data, flow_style=True,
        )
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=False,
    )


def _double_quote_representer(dumper: SafeDumper, data: str) -> yaml.Node:
    """Use double quotes when quoting is needed, plain style otherwise."""
    # If the string needs quoting (empty, has special chars, looks like
    # a YAML value), use double quotes instead of PyYAML's default single.
    if dumper.resolve(yaml.ScalarNode, data, (True, False)) != "tag:yaml.org,2002:str":
        # Looks like a non-string scalar (bool, null, number) — must quote
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style='"',
        )
    if not data or data != data.strip() or ":" in data or "#" in data:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style='"',
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def _double_quote_representer(dumper: SafeDumper, data: str) -> yaml.Node:
    """Prefer double quotes over single when quoting is needed."""
    tag = "tag:yaml.org,2002:str"
    # Check if YAML would misinterpret this as a non-string (bool, null, etc.)
    needs_quoting = (
        dumper.resolve(yaml.ScalarNode, data, (True, False)) != tag
        or not data
        or data != data.strip()
        or ":" in data
        or "#" in data
    )
    if needs_quoting:
        return dumper.represent_scalar(tag, data, style='"')
    return dumper.represent_scalar(tag, data)


_FlowListDumper.add_representer(list, _flow_list_representer)
_FlowListDumper.add_representer(str, _double_quote_representer)
_FlowListDumper.add_representer(str, _double_quote_representer)


class _SpecYAMLHandler(frontmatter.default_handlers.YAMLHandler):
    """YAMLHandler that preserves inline lists and key order."""

    def export(self, metadata: dict[str, object], **kwargs: object) -> str:
        kwargs.setdefault("Dumper", _FlowListDumper)
        kwargs.setdefault("default_flow_style", False)
        kwargs.setdefault("allow_unicode", True)
        kwargs.setdefault("sort_keys", False)
        metadata_str = yaml.dump(metadata, **kwargs).strip()  # type: ignore[call-overload]
        return metadata_str


_spec_yaml_handler = _SpecYAMLHandler()

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
        if isinstance(value, list) and not value:
            continue
        if isinstance(value, str) and not value:
            continue
        # Clean nested sub-model dicts (e.g. links): drop None/empty values
        if isinstance(value, dict):
            cleaned = {
                k: v
                for k, v in value.items()
                if v is not None and not (isinstance(v, list) and not v)
            }
            if not cleaned:
                continue
            value = cleaned
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
    return frontmatter.dumps(post, handler=_spec_yaml_handler) + "\n"


__all__ = [
    "ParseError",
    "parse_frontmatter",
    "parse_spec_file",
    "render_spec",
    "write_spec_file",
]
