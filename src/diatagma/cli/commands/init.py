"""Init command — scaffold a .specs/ directory."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from diatagma.cli.app import app
from diatagma.cli.output import print_error, print_success
from diatagma.cli.state import GlobalState

_DEFAULT_SETTINGS = """\
# Diatagma settings
default_assignee: ""
statuses:
  - pending
  - in-progress
  - review
  - done
  - cancelled
types:
  - feature
  - bug
  - chore
  - docs
  - epic
  - spike
auto_complete_parent: true
"""

_DEFAULT_PREFIXES = """\
# Spec ID prefixes — add one per project/team
# PROJ:
#   name: "My Project"
#   template: story
"""

_DEFAULT_GITIGNORE = """\
# Diatagma cache (regenerated from spec files)
.cache/
"""

_DEFAULT_STORY_TEMPLATE = """\
## Description

<!-- What needs to be done and why -->

## Behavior

### Scenario: Happy path

- **Given** ...
- **When** ...
- **Then** ...

## Constraints

<!-- Technical constraints, performance requirements, etc. -->

## Verification

- [ ] ...
"""


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
) -> None:
    """Scaffold a .specs/ directory in the current project."""
    specs_dir = GlobalState.specs_dir

    if specs_dir.exists() and any(specs_dir.iterdir()):
        print_error(f"{specs_dir} already exists and is not empty.")

    specs_dir.mkdir(parents=True, exist_ok=True)
    config_dir = specs_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (specs_dir / "backlog").mkdir(exist_ok=True)
    (specs_dir / "archive").mkdir(exist_ok=True)
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Write default config files
    (config_dir / "settings.yaml").write_text(_DEFAULT_SETTINGS, encoding="utf-8")
    (specs_dir / ".gitignore").write_text(_DEFAULT_GITIGNORE, encoding="utf-8")
    (templates_dir / "story.md").write_text(_DEFAULT_STORY_TEMPLATE, encoding="utf-8")

    # Write prefixes if provided
    if prefix:
        prefix_name = name or prefix
        prefixes_content = f"""\
{prefix}:
  name: "{prefix_name}"
  template: story
"""
        (config_dir / "prefixes.yaml").write_text(prefixes_content, encoding="utf-8")
    else:
        (config_dir / "prefixes.yaml").write_text(_DEFAULT_PREFIXES, encoding="utf-8")

    # Write empty changelog
    (specs_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")

    if not GlobalState.quiet:
        print_success(f"Initialized {specs_dir}")
        print_success("  config/     — settings, prefixes, templates")
        print_success("  backlog/    — deferred specs")
        print_success("  archive/    — completed specs")
        print_success("  changelog.md")
        if prefix:
            print_success(f"  Prefix '{prefix}' configured.")
        else:
            print_success("  Edit config/prefixes.yaml to add your first prefix.")
