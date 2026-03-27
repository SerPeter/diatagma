"""Dependency graph powered by networkx.

Builds and maintains a DAG of task dependencies. Provides cycle
detection, topological sorting, blocked/unblocked status computation,
and critical path analysis.

Key class:
    TaskGraph
        .build(tasks: list[Task])
        .is_blocked(task_id) → bool
        .get_unblocked()     → list[str]  (task IDs ready to work)
        .get_blockers(task_id) → list[str]
        .get_dependents(task_id) → list[str]
        .topological_sort()  → list[str]
        .detect_cycles()     → list[list[str]]
        .critical_path()     → list[str]
"""
