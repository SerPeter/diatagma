"""Frontmatter validation against configurable schema rules.

Loads field requirements from .tasks/config/schema.yaml and validates
spec frontmatter. Supports per-status required fields (e.g. in-progress
requires assignee) and field-level type/enum constraints.

Key functions:
    validate_spec(spec: Spec, schema_config) → list[ValidationError]
    validate_all(specs: list[Spec], schema_config) → dict[str, list[ValidationError]]
"""
