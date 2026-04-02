"""Init command — scaffold a .specs/ directory and optional agent integrations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_error, print_success, print_warning
from diatagma.cli.state import GlobalState

_DEFAULT_SETTINGS = """\
# Diatagma settings
# -----------------
# These control tool behavior. Spec files themselves remain the source of truth.

# Default assignee for new specs (leave empty for unassigned)
default_assignee: ""

# Statuses available for specs (order matters for kanban columns)
statuses:
  - pending
  - blocked
  - in-progress
  - in-review
  - done
  - cancelled

# Spec types (each has a corresponding template and file extension)
types:
  - story     # .story.md — unit of deliverable work
  - epic      # .epic.md  — groups related stories
  - spike     # .spike.md — research producing ADRs/docs
  - bug       # .bug.md   — defect report with reproduction steps

# Story point scale (Fibonacci)
story_point_scale: [1, 2, 3, 5, 8, 13, 21]

# Business value range (log-scaled importance)
business_value_range: [-1000, 1000]

# Agent claim timeout in minutes (auto-release if agent doesn't heartbeat)
claim_timeout_minutes: 30

# Auto-complete parent when all children are done
auto_complete_parent: true

# Web dashboard port
web_port: 8742

# MCP transport: "stdio" or "streamable-http"
mcp_transport: "stdio"
"""

_DEFAULT_PREFIXES = """\
# Spec ID prefixes — add one per project/team
# Max 5 uppercase letters. Numbers start at 001 and grow as needed.
# PROJ:
#   description: "My Project"
#   template: story
"""

_DEFAULT_SCHEMA = """\
# Frontmatter schema — validation rules for spec metadata
# -------------------------------------------------------

# Fields present on every spec
required_fields:
  - id
  - title
  - status
  - type
  - created

# Fields required when status transitions
required_by_status:
  in-progress:
    - assignee
  in-review:
    - assignee
  done:
    - assignee

# Field type constraints
field_types:
  id:
    type: string
    pattern: "^[A-Z]{1,5}-\\\\d{3,}$"
  title:
    type: string
    max_length: 120
  status:
    type: enum
    values: [pending, blocked, in-progress, in-review, done, cancelled]
  type:
    type: enum
    values: [story, epic, spike, bug]
  business_value:
    type: integer
    min: -1000
    max: 1000
  story_points:
    type: enum
    values: [1, 2, 3, 5, 8, 13, 21]
  tags:
    type: list
    item_type: string
  blocked_by:
    type: list
    item_type: string
    pattern: "^[A-Z]{1,5}-\\\\d{3,}$"
  relates_to:
    type: list
    item_type: string
    pattern: "^[A-Z]{1,5}-\\\\d{3,}$"
  assignee:
    type: string
  due_date:
    type: date
  cycle:
    type: string
  parent:
    type: string
    pattern: "^[A-Z]{1,5}-\\\\d{3,}$"
"""

_DEFAULT_PRIORITY = """\
# Priority scoring configuration (WSJF-style)
# ---------------------------------------------
# priority = (business_value * w_bv + time_criticality * w_tc + risk_reduction * w_rr)
#            / max(story_points, 1)
#            + blocked_bonus * unblocks_count
#            + age_bonus * days_since_created
#            + due_date_urgency

weights:
  business_value: 1.0
  time_criticality: 0.5    # derived from due_date proximity
  risk_reduction: 0.3      # manual field, optional

  # Bonus per spec that this spec unblocks
  unblocks_bonus: 50.0

  # Bonus per day since spec was created (prevents starvation)
  age_bonus_per_day: 0.5

  # Urgency multiplier when due date is within N days
  due_date_urgency:
    critical_days: 3       # max urgency boost
    warning_days: 7        # moderate urgency boost
    critical_bonus: 200.0
    warning_bonus: 50.0
"""

_DEFAULT_HOOKS = """\
# Lifecycle hooks — triggered on spec state changes
# --------------------------------------------------
# Each hook specifies a trigger condition and an action.

# hooks:
#   on_status_change:
#     - when:
#         status: done
#       action: move_to_archive
#
#   on_create:
#     - action: validate_frontmatter
#
#   on_claim_timeout:
#     - action: release_and_notify
"""

_DEFAULT_CYCLES = """\
# Cycle definitions
# ------------------
# Define cycle boundaries for planning and velocity tracking.

# cycles:
#   - name: "Cycle 1"
#     start: 2026-04-01
#     end: 2026-04-14
#     goal: "Core models and parser"
#
#   - name: "Cycle 2"
#     start: 2026-04-14
#     end: 2026-04-28
#     goal: "MCP server and CLI"
"""

_DEFAULT_GITIGNORE = """\
# Diatagma cache (regenerated from spec files)
.cache/
"""

_DEFAULT_STORY_TEMPLATE = """\
---
id: ""
title: ""
status: pending
type: feature
tags: [refine]
business_value: 0
story_points: 1
parent: ""
assignee: ""
created: ""
---

## Description

<!-- One-line summary of what the user/agent experiences when this is done -->

## Context

<!-- Why this story exists — what problem it solves, what user need it addresses.
     Link to ADRs or research docs that informed this decision. -->

## Behavior

<!-- Spec-driven scenarios in Given/When/Then format.
     These are the contract — tests are derived from these. -->

### Scenario: [name]

- **Given** [precondition]
- **When** [action]
- **Then** [expected outcome]

## Constraints

<!-- Non-functional requirements, boundaries, performance targets.
     What must NOT happen is as important as what must. -->

## Verification

<!-- How to confirm this story is done. Maps directly to test suites.
     Workflow: write spec → derive tests from behavior → implement → verify. -->

- [ ] ...

## References

<!-- Links to ADRs, research docs, related specs, or external resources -->

---
<!-- Fill during/after implementation -->

## Implementation Summary

<!-- Filled at completion. Concise digest of what was built, key decisions,
     and outcomes — so future readers don't need to parse the full spec. -->

## Implementation Notes

<!-- Filled during implementation. Append decisions, trade-offs, and
     references as work progresses. -->
"""

_DEFAULT_EPIC_TEMPLATE = """\
---
id: ""
title: ""
status: pending
type: epic
tags: [refine]
business_value: 0
story_points: 0
assignee: ""
created: ""
---

## Vision

<!-- What does the world look like when this epic is done?
     Describe the end state from the user's perspective. -->

## Context

<!-- Why this epic exists — what strategic goal it serves.
     Link to roadmap phase and any ADRs that shaped it. -->

## Stories

<!-- Child stories that compose this epic.
     Maintained manually or aggregated from specs with parent: THIS_ID. -->

- [ ] ...

## Behavior

<!-- High-level scenarios that define epic-level acceptance.
     Individual stories have their own detailed scenarios. -->

### Scenario: [end-to-end flow name]

- **Given** [precondition]
- **When** [user/agent completes the full workflow]
- **Then** [observable outcome]

## Constraints

<!-- Cross-cutting concerns that apply to all child stories. -->

## Verification

<!-- Epic-level acceptance criteria — what must be true for the epic to close. -->

- [ ] All child stories are done
- [ ] ...

## References

<!-- Roadmap phase, ADRs, research docs, architecture docs -->
"""

_DEFAULT_SPIKE_TEMPLATE = """\
---
id: ""
title: ""
status: pending
type: spike
tags: [refine]
business_value: 0
story_points: 1
parent: ""
assignee: ""
created: ""
---

## Description

<!-- One-line summary of the research question or exploration -->

## Context

<!-- Why this spike is needed — what decision it unblocks.
     Link to the story or epic that triggered this spike. -->

## Research Questions

<!-- Specific questions to answer. Each should have a clear "answered"
     state so the spike has a natural end point. -->

1. ...

## Findings

<!-- Filled during research. Document answers to each question above,
     with evidence and links. -->

## Deliverables

<!-- What this spike produces. At least one of: -->

- [ ] ADR at `docs/adr/NNN-slug.md` — for architectural decisions
- [ ] Research doc at `docs/research/YYMMDD_slug.md` — for detailed findings

---
<!-- Fill during/after research -->

## Recommendation

<!-- Summary conclusion and proposed next steps based on findings.
     Should be actionable — "do X" not "maybe consider X". -->

## Implementation Summary

<!-- Filled at completion. Concise digest of what was researched, key findings,
     and outcomes — so future readers don't need to parse the full spec. -->

## Implementation Notes

<!-- Filled during research. Append decisions, dead ends, and
     references as work progresses. -->
"""

_DEFAULT_BUG_TEMPLATE = """\
---
id: ""
title: ""
status: pending
type: bug
tags: [refine]
business_value: 0
story_points: 1
parent: ""
assignee: ""
created: ""
---

<!-- Fill before starting work -->

## Description

<!-- One-line summary of the defect -->

## Current Behavior

<!-- What happens now? Include error messages, stack traces, or screenshots. -->

## Expected Behavior

<!-- What should happen instead? -->

## Reproduction Steps

<!-- Minimal steps to reproduce the issue. Be specific. -->

1. ...

## Environment

<!-- Relevant context: OS, Python version, browser, config, etc. -->

## References

<!-- Links to related specs, logs, or discussions -->

---
<!-- Fill during/after investigation -->

## Root Cause

<!-- What actually went wrong and why. -->

## Verification

<!-- How to confirm the fix works. -->

- [ ] Reproduction steps no longer produce the bug
- [ ] ...

## Prevention

<!-- What should change to prevent similar bugs in the future?
     Examples: add a test, tighten validation, improve error handling. -->

## Implementation Summary

<!-- Filled at completion. Concise digest of what was fixed, root cause,
     and outcomes — so future readers don't need to parse the full spec. -->

## Implementation Notes

<!-- Append decisions, trade-offs, and references as work progresses. -->
"""

_DEFAULT_ROADMAP = """\
# Roadmap

<!-- High-level phases for your project. Link to epics and stories. -->

## Phase 1: [Name]

**Goal**: ...

- ...
"""


def _find_repo_root(start: Path) -> Path:
    """Walk up from start to find a .git directory. Fall back to start."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return start


def _install_skill(repo_root: Path, *, update: bool = False) -> None:
    """Write the skill file and user-preferences template."""
    from diatagma.core.agents_md import render_skill, render_user_preferences

    skill_dir = repo_root / ".claude" / "skills" / "diatagma"
    skill_path = skill_dir / "skill.md"
    prefs_path = skill_dir / "references" / "user-preferences.md"

    if skill_path.exists() and not update:
        print_error(
            f"{skill_path} already exists. Use --update to regenerate."
        )

    # Try to load project config for project-specific content
    config = None
    specs_dir = GlobalState.specs_dir
    if specs_dir.exists():
        from diatagma.core.config import DiatagmaConfig

        try:
            config = DiatagmaConfig(specs_dir)
        except Exception:
            pass  # Generate without config — still useful

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)

    skill_path.write_text(render_skill(config), encoding="utf-8")
    print_success(f"  {skill_path.relative_to(repo_root)}")

    # Never overwrite user preferences
    if not prefs_path.exists():
        prefs_path.write_text(render_user_preferences(), encoding="utf-8")
        print_success(f"  {prefs_path.relative_to(repo_root)}")
    elif not update:
        print_success(f"  {prefs_path.relative_to(repo_root)} (exists, kept)")


def _install_agents_md(repo_root: Path) -> None:
    """Append a DIATAGMA section to AGENTS.md or CLAUDE.md."""
    from diatagma.core.agents_md import render_agents_md_section

    marker = "## Diatagma"

    # Find the target file: prefer AGENTS.md, fall back to CLAUDE.md
    agents_path = repo_root / "AGENTS.md"
    claude_path = repo_root / "CLAUDE.md"

    if agents_path.exists():
        target = agents_path
    elif claude_path.exists():
        target = claude_path
    else:
        print_warning(
            "No AGENTS.md or CLAUDE.md found. Create one first, then re-run with --agents-md."
        )
        return

    content = target.read_text(encoding="utf-8")
    if marker in content:
        print_success(f"  {target.name} already has a Diatagma section (skipped).")
        return

    if not content.endswith("\n"):
        content += "\n"
    content += "\n" + render_agents_md_section()
    target.write_text(content, encoding="utf-8")
    print_success(f"  {target.name} (appended Diatagma section)")


@app.command()
def init(
    prefix: Annotated[
        Optional[str],
        typer.Option("--prefix", "-p", help="Initial prefix to configure."),
    ] = None,
    name: Annotated[
        Optional[str],
        typer.Option("--name", help="Project name for the prefix."),
    ] = None,
    skill: Annotated[
        bool,
        typer.Option("--skill", help="Install Claude Code skill for diatagma CLI."),
    ] = False,
    update: Annotated[
        bool,
        typer.Option("--update", help="Regenerate skill file (preserves user-preferences)."),
    ] = False,
    agents_md: Annotated[
        bool,
        typer.Option("--agents-md", help="Add a Diatagma section to AGENTS.md."),
    ] = False,
) -> None:
    """Scaffold a .specs/ directory in the current project."""
    specs_dir = GlobalState.specs_dir
    repo_root = _find_repo_root(specs_dir)

    # --update implies --skill
    if update:
        skill = True

    # Skill-only mode: don't require .specs/ scaffolding
    if skill and specs_dir.exists() and any(specs_dir.iterdir()):
        if not GlobalState.quiet:
            print_success("Installing skill...")
        _install_skill(repo_root, update=update)
        if agents_md:
            _install_agents_md(repo_root)
        return

    # --agents-md only mode
    if agents_md and not skill and specs_dir.exists() and any(specs_dir.iterdir()):
        _install_agents_md(repo_root)
        return

    # Full init: scaffold .specs/
    if specs_dir.exists() and any(specs_dir.iterdir()):
        print_error(f"{specs_dir} already exists and is not empty.")

    specs_dir.mkdir(parents=True, exist_ok=True)
    config_dir = specs_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (specs_dir / "backlog").mkdir(exist_ok=True)
    (specs_dir / "archive").mkdir(exist_ok=True)
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Write config files
    (config_dir / "settings.yaml").write_text(_DEFAULT_SETTINGS, encoding="utf-8")
    (config_dir / "schema.yaml").write_text(_DEFAULT_SCHEMA, encoding="utf-8")
    (config_dir / "priority.yaml").write_text(_DEFAULT_PRIORITY, encoding="utf-8")
    (config_dir / "hooks.yaml").write_text(_DEFAULT_HOOKS, encoding="utf-8")
    (config_dir / "cycles.yaml").write_text(_DEFAULT_CYCLES, encoding="utf-8")
    (specs_dir / ".gitignore").write_text(_DEFAULT_GITIGNORE, encoding="utf-8")

    # Write templates
    (templates_dir / "story.md").write_text(_DEFAULT_STORY_TEMPLATE, encoding="utf-8")
    (templates_dir / "epic.md").write_text(_DEFAULT_EPIC_TEMPLATE, encoding="utf-8")
    (templates_dir / "spike.md").write_text(_DEFAULT_SPIKE_TEMPLATE, encoding="utf-8")
    (templates_dir / "bug.md").write_text(_DEFAULT_BUG_TEMPLATE, encoding="utf-8")

    # Write prefixes
    if prefix:
        prefix_name = name or prefix
        prefixes_content = f"""\
{prefix}:
  description: "{prefix_name}"
  template: story
"""
        (config_dir / "prefixes.yaml").write_text(prefixes_content, encoding="utf-8")
    else:
        (config_dir / "prefixes.yaml").write_text(_DEFAULT_PREFIXES, encoding="utf-8")

    # Write changelog and roadmap
    (specs_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    (specs_dir / "ROADMAP.md").write_text(_DEFAULT_ROADMAP, encoding="utf-8")

    if not GlobalState.quiet:
        print_success(f"Initialized {specs_dir}")
        print_success("  config/       settings, schema, priority, hooks, cycles, prefixes")
        print_success("  templates/    story, epic, spike, bug")
        print_success("  backlog/      deferred specs")
        print_success("  archive/      completed specs")
        print_success("  changelog.md")
        print_success("  ROADMAP.md")
        if prefix:
            print_success(f"  Prefix '{prefix}' configured.")
        else:
            print_success("  Edit config/prefixes.yaml to add your first prefix.")

    if skill:
        _install_skill(repo_root, update=update)

    if agents_md:
        _install_agents_md(repo_root)
