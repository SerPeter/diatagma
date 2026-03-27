"""MCP tool definitions for AI agent interaction.

Each tool is a thin wrapper around core library functions, decorated
with @mcp.tool(). Input/output types are Pydantic models for automatic
schema generation.

Tools:
    create_story(prefix, title, **meta) — create a new spec file from template
    get_story(spec_id)                  — read a single spec
    update_story(spec_id, **changes)    — modify spec metadata or body
    list_stories(filters, sort_by)      — list/filter/sort specs
    get_next_story(filters)             — highest priority unblocked story
    search_stories(query)               — full-text search
    claim_story(spec_id, agent_id)      — lock a spec for an agent
    release_story(spec_id, agent_id)    — release a claimed spec
    get_dependency_graph(spec_id)       — show blockers and dependents
    validate_specs()                    — check all specs against schema
"""
