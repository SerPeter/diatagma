"""SpecStore — CRUD operations over the .tasks/ directory.

The single source-of-truth layer. Every read/write goes through the
filesystem. The store discovers spec files by scanning configured
directories, delegates parsing to parser.py, and coordinates with
cache.py for acceleration.

File extensions determine spec type:
    .story.md  — stories (features, bugs, chores, docs)
    .epic.md   — epics
    .spike.md  — research spikes

Key class:
    SpecStore(tasks_dir: Path)
        .list(filters, sort_by)  → list[Spec]
        .get(spec_id)            → Spec
        .create(prefix, title, spec_type, template, **meta) → Spec
        .update(spec_id, **changes)
        .move_to_backlog(spec_id)
        .move_to_archive(spec_id)
        .next_id(prefix)         → str  (e.g. "DIA-004")
"""
