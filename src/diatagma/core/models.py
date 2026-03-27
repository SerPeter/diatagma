"""Pydantic models for specs, frontmatter metadata, and configuration.

Defines the canonical shape of a spec — both the YAML frontmatter fields
and the parsed markdown body sections. Used by parser.py for
serialization and by schema.py for validation.

All spec types (story, epic, spike, bug, chore, docs) share the same
model structure. The ``type`` field distinguishes them; file extensions
(`.story.md`, `.epic.md`, `.spike.md`) provide visual identification.

Epics are specs too — they get their own ID, body, acceptance criteria,
and participate in the dependency graph. Child specs reference their
parent via the ``parent`` field using the parent's spec ID.

Key models:
    SpecMeta     — frontmatter fields (id, title, status, type, tags, parent, etc.)
    SpecBody     — parsed markdown sections (description, context, behavior, etc.)
    Spec         — SpecMeta + SpecBody + file path
    SpecConfig   — loaded from .tasks/config/settings.yaml
    PrefixDef    — prefix definition from prefixes.yaml
"""
