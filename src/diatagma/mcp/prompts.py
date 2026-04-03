"""MCP prompt definitions — workflow templates for AI agents.

Prompts provide structured message sequences that guide agents through
multi-step workflows like story creation, spike research, and backlog triage.

Key function:
    register_prompts(mcp, specs_dir) → None
"""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from diatagma.core.context import create_context


# ---------------------------------------------------------------------------
# Prompt registration
# ---------------------------------------------------------------------------


def register_prompts(mcp: FastMCP, specs_dir: Path) -> None:
    """Register all MCP prompts on the server instance."""

    @mcp.prompt(
        description="Guided workflow for creating a well-formed story spec.",
    )
    def create_story(title: str, prefix: str | None = None) -> str:
        """Walk the agent through creating a new story."""
        ctx = create_context(specs_dir)
        prefixes = list(ctx.config.prefixes.keys())
        statuses = ctx.config.settings.statuses
        types = ctx.config.settings.types
        points = ctx.config.settings.story_point_scale

        resolved_prefix = prefix or (prefixes[0] if prefixes else "PROJ")

        return (
            f"Create a new story spec with the title: {title!r}\n\n"
            f"Use prefix: {resolved_prefix} "
            f"(available: {', '.join(prefixes)})\n\n"
            "Follow these steps:\n\n"
            "1. **Create the spec** using the `create_spec` tool with:\n"
            f"   - title: {title!r}\n"
            f"   - prefix: {resolved_prefix!r}\n"
            "   - type: 'feature' (or choose from: "
            f"{', '.join(types)})\n\n"
            "2. **Set priority fields** using `update_spec`:\n"
            f"   - business_value: integer (-1000 to 1000)\n"
            f"   - story_points: one of {points}\n\n"
            "3. **Write the spec body** using `update_spec` with:\n"
            "   - description: one-line summary of the feature\n\n"
            "4. **Add dependencies** if this spec is blocked by other work.\n\n"
            f"Valid statuses: {', '.join(statuses)}\n"
        )

    @mcp.prompt(
        description="Guided workflow for conducting a research spike.",
    )
    def run_spike(topic: str, prefix: str | None = None) -> str:
        """Walk the agent through a spike workflow."""
        ctx = create_context(specs_dir)
        prefixes = list(ctx.config.prefixes.keys())
        resolved_prefix = prefix or (prefixes[0] if prefixes else "PROJ")

        return (
            f"Conduct a research spike on: {topic!r}\n\n"
            "Follow these steps:\n\n"
            "1. **Create the spike spec** using `create_spec` with:\n"
            f"   - title: {topic!r}\n"
            f"   - prefix: {resolved_prefix!r}\n"
            "   - type: 'spike'\n\n"
            "2. **Define research questions** — what specific questions "
            "need answering?\n\n"
            "3. **Research each question** — use available tools and "
            "resources to investigate.\n\n"
            "4. **Document findings** — update the spec body with:\n"
            "   - Key findings per research question\n"
            "   - Trade-offs discovered\n"
            "   - Recommendation\n\n"
            "5. **Produce deliverables**:\n"
            "   - ADR document if an architectural decision was made\n"
            "   - Research document with detailed findings\n"
            "   - Follow-up story specs for implementation work\n\n"
            "6. **Complete the spike** — set status to 'done' using "
            "`update_spec`.\n"
        )

    @mcp.prompt(
        description="Review and prioritize pending backlog items.",
    )
    def triage_backlog() -> str:
        """Guide the agent through backlog triage."""
        ctx = create_context(specs_dir)
        settings = ctx.config.settings

        return (
            "Triage the pending backlog by following these steps:\n\n"
            "1. **List pending specs** using `list_specs` with "
            "status='pending'.\n\n"
            "2. **Review each spec** — for each pending item:\n"
            "   - Read the full spec with `get_spec`\n"
            "   - Assess business value and effort\n"
            "   - Check for missing information\n\n"
            "3. **Prioritize** — update each spec with:\n"
            f"   - business_value: integer (-1000 to 1000)\n"
            f"   - story_points: one of "
            f"{settings.story_point_scale}\n\n"
            "4. **Identify blockers** — check the dependency graph with "
            "`get_dependency_graph` and note any cycles or missing "
            "dependencies.\n\n"
            "5. **Validate** — run `validate_specs` to catch any "
            "inconsistencies introduced during triage.\n\n"
            "6. **Report** — summarize:\n"
            "   - Total specs reviewed\n"
            "   - Priority distribution\n"
            "   - Blocked items and why\n"
            "   - Recommended next actions\n"
        )
