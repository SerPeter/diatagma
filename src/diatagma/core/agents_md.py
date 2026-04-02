"""Generate agent instruction content from config and CLI introspection.

Produces deterministic markdown for:
- Skill file (.claude/skills/diatagma/skill.md) — full CLI reference
- AGENTS.md snippet — short section for repos using diatagma

The CLI reference is introspected from the actual typer app so it
cannot drift from the real commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
import typer

if TYPE_CHECKING:
    from diatagma.core.config import DiatagmaConfig


# ---------------------------------------------------------------------------
# CLI introspection
# ---------------------------------------------------------------------------


def _introspect_cli() -> list[dict[str, str]]:
    """Extract command info from the typer app via click internals.

    Returns a list of dicts with keys: name, help, usage.
    """
    from diatagma.cli.app import app

    click_app = typer.main.get_command(app)
    commands: list[dict[str, str]] = []

    for name, cmd in sorted(click_app.commands.items()):
        args: list[str] = []
        opts: list[str] = []
        for p in cmd.params:
            if isinstance(p, click.Argument):
                args.append(f"<{p.name}>")
            elif p.name != "help":
                primary = p.opts[0] if p.opts else p.name
                if p.is_flag:
                    opts.append(primary)
                else:
                    opts.append(f"{primary} <value>")

        usage_parts = ["diatagma", name, *args]
        if opts:
            usage_parts.append(f"[{' | '.join(opts)}]")

        commands.append({
            "name": name,
            "help": cmd.help or "",
            "usage": " ".join(usage_parts),
        })

    return commands


# ---------------------------------------------------------------------------
# Skill content
# ---------------------------------------------------------------------------

_SKILL_HEADER = """\
---
name: diatagma
description: Spec-driven story coordination — find work, claim specs, update status via CLI
---

# Diatagma CLI Reference

Diatagma manages work as markdown spec files with YAML frontmatter in a `.specs/` directory.
Use the CLI commands below to interact with specs. Always prefer `--json` for machine-readable output.

Check `references/user-preferences.md` for project-specific conventions and preferences.
"""

_SKILL_WORKFLOW = """
## Workflow

The standard agent workflow for completing work:

1. **Find ready work:** `diatagma next --json` returns priority-sorted specs with no unresolved blockers
2. **Read the spec:** `diatagma show <id>` to understand requirements and acceptance criteria
3. **Claim it:** `diatagma status <id> in-progress` to signal you're working on it
4. **Do the work:** implement what the spec describes
5. **Mark review:** `diatagma status <id> in-review` when ready for review
6. **Complete:** `diatagma status <id> done` when accepted

## Tips

- Use `diatagma list --status pending` to see all unstarted work
- Use `diatagma validate` to check for broken dependencies or schema issues
- Use `diatagma next --type bug` to focus on bugs only
- All commands support `--json` for structured output
- Use `diatagma edit <id> --field assignee <name>` to claim ownership
"""


def render_skill(config: DiatagmaConfig | None = None) -> str:
    """Render the full skill file content.

    If config is provided, includes project-specific prefixes and statuses.
    """
    parts: list[str] = [_SKILL_HEADER.lstrip()]

    # Project config section (if available)
    if config is not None:
        parts.append(_render_config_section(config))

    # CLI reference from introspection
    parts.append(_render_cli_reference())

    # Workflow
    parts.append(_SKILL_WORKFLOW.strip())

    return "\n\n".join(parts) + "\n"


def _render_config_section(config: DiatagmaConfig) -> str:
    """Render project-specific configuration."""
    lines = ["## Project Configuration"]

    if config.prefixes:
        lines.append("")
        lines.append("**Prefixes:**")
        for prefix, defn in config.prefixes.items():
            lines.append(f"- `{prefix}` — {defn.description}")

    lines.append("")
    lines.append(f"**Statuses:** {', '.join(f'`{s}`' for s in config.settings.statuses)}")
    lines.append(f"**Types:** {', '.join(f'`{s}`' for s in config.settings.types)}")

    if config.settings.story_point_scale:
        scale = ", ".join(str(p) for p in config.settings.story_point_scale)
        lines.append(f"**Story points:** {scale}")

    return "\n".join(lines)


def _render_cli_reference() -> str:
    """Render CLI command reference from introspection."""
    commands = _introspect_cli()
    lines = ["## Commands", ""]

    for cmd in commands:
        lines.append(f"### `{cmd['usage']}`")
        if cmd["help"]:
            lines.append(f"{cmd['help']}")
        lines.append("")

    lines.append("**Global options:** `--specs-dir <path>`, `--json`, `--quiet`, `--no-color`")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# AGENTS.md snippet
# ---------------------------------------------------------------------------

_AGENTS_MD_SNIPPET = """\
## Diatagma

This project uses [diatagma](https://github.com/peterHoburg/diatagma) for spec-driven story coordination.
Work items live as markdown files in `.specs/`. Run `diatagma next --json` to find the highest-priority
actionable work. See the `/diatagma` skill for full CLI reference and workflow.
"""


def render_agents_md_section() -> str:
    """Render a short DIATAGMA section for inclusion in AGENTS.md."""
    return _AGENTS_MD_SNIPPET


# ---------------------------------------------------------------------------
# User preferences template
# ---------------------------------------------------------------------------

_USER_PREFERENCES = """\
# User Preferences

<!-- Add project-specific conventions for AI agents working with diatagma specs.
     This file is never overwritten by `diatagma init --update`.

     Examples:
     - Preferred commit message format
     - Branch naming conventions
     - Testing requirements before marking specs done
     - Spec writing style preferences
-->
"""


def render_user_preferences() -> str:
    """Render the empty user-preferences template."""
    return _USER_PREFERENCES


__all__ = [
    "render_agents_md_section",
    "render_skill",
    "render_user_preferences",
]
