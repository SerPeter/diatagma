"""Load and merge configuration from .tasks/config/.

Reads settings.yaml, prefixes.yaml, schema.yaml, priority.yaml,
sprints.yaml, and hooks.yaml. Provides typed access via Pydantic
settings models.

Key class:
    DiatagmaConfig(tasks_dir: Path)
        .settings   → Settings
        .prefixes   → dict[str, PrefixDef]
        .schema     → SchemaConfig
        .priority   → PriorityConfig
        .sprints    → list[Sprint]
        .hooks      → HooksConfig
        .templates  → dict[str, str]  (spec_type → template content)
"""
