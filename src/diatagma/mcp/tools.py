"""MCP tool definitions for AI agent interaction.

Each tool is a thin wrapper around core library functions, decorated
with @mcp.tool(). Input/output types are Pydantic models for automatic
schema generation.

Tools:
    create_task(prefix, title, **meta)  — create a new task file from template
    get_task(task_id)                   — read a single task
    update_task(task_id, **changes)     — modify task metadata or body
    list_tasks(filters, sort_by)        — list/filter/sort tasks
    get_next_task(filters)              — highest priority unblocked task
    search_tasks(query)                 — full-text search
    claim_task(task_id, agent_id)       — lock a task for an agent
    release_task(task_id, agent_id)     — release a claimed task
    get_dependency_graph(task_id)       — show blockers and dependents
    validate_tasks()                    — check all tasks against schema
"""
