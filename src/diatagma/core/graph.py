"""Dependency graph powered by networkx.

Builds and maintains a DAG of spec dependencies. Provides cycle
detection, topological sorting, blocked/unblocked status computation,
and critical path analysis.

Key class:
    SpecGraph
        .build(specs: list[Spec])
        .is_blocked(spec_id) → bool
        .get_unblocked()     → list[str]  (spec IDs ready to work)
        .get_blockers(spec_id) → list[str]
        .get_dependents(spec_id) → list[str]
        .topological_sort()  → list[str]
        .detect_cycles()     → list[list[str]]
        .critical_path()     → list[str]
"""
