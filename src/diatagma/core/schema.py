"""Frontmatter validation against configurable schema rules.

Loads field requirements from .tasks/config/schema.yaml and validates
task frontmatter. Supports per-status required fields (e.g. in-progress
requires assignee) and field-level type/enum constraints.

Key functions:
    validate_task(task: Task, schema_config) → list[ValidationError]
    validate_all(tasks: list[Task], schema_config) → dict[str, list[ValidationError]]
"""
