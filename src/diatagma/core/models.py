"""Pydantic models for tasks, frontmatter metadata, and configuration.

Defines the canonical shape of a task — both the YAML frontmatter fields
and the parsed markdown body sections. Used by parser.py for
serialization and by schema.py for validation.

Key models:
    TaskMeta     — frontmatter fields (id, title, status, type, tags, parent, etc.)
    TaskBody     — parsed markdown sections (description, context, etc.)
    Task         — TaskMeta + TaskBody + file path
    TaskConfig   — loaded from .tasks/config/settings.yaml
    PrefixDef    — prefix definition from prefixes.yaml

Epics are tasks too (type: epic). Child tasks reference their parent
via the `parent` field using the parent's task ID (e.g. parent: DIA-011).
This replaces a flat `epic` string field — epics get their own ID,
body, acceptance criteria, and participate in the dependency graph.
"""
