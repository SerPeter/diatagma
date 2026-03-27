"""Append-only changelog for task mutations.

Writes structured, diff-friendly entries to .tasks/changelog.md.
One line per change, grouped by date. Git-friendly, grep-friendly.

Format:
    ## 2026-03-27
    - DIA-001: status pending → in-progress (agent: claude-abc)
    - DIA-002: created (agent: human)
    - DIA-003: business_value 100 → 300 (agent: human)

Key functions:
    append_entry(task_id, field, old, new, agent_id)
    read_entries(since: date | None) → list[ChangelogEntry]
"""
