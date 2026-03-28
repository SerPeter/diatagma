"""Shared test fixtures.

Provides:
    tmp_tasks_dir      — a temporary .tasks/ directory with config and sample specs
    sample_meta_dict   — a raw dict simulating parsed YAML frontmatter
    sample_spec        — a parsed Spec object for unit tests
    sample_spec_text   — a complete markdown string with frontmatter + body
    minimal_spec_text  — frontmatter only, no body
    spec_with_extras   — includes unknown sections
    spec_store         — a SpecStore pointed at tmp_tasks_dir
"""

from datetime import date

import pytest

from diatagma.core.models import PrefixDef, Spec, SpecBody, SpecMeta
from diatagma.core.parser import write_spec_file
from diatagma.core.store import SpecStore


@pytest.fixture
def tmp_tasks_dir(tmp_path):
    """Create a minimal .tasks/ directory structure for testing."""
    tasks_dir = tmp_path / ".tasks"
    tasks_dir.mkdir()
    (tasks_dir / "config").mkdir()
    (tasks_dir / "backlog").mkdir()
    (tasks_dir / "archive").mkdir()
    (tasks_dir / ".cache").mkdir()
    return tasks_dir


@pytest.fixture
def sample_meta_dict() -> dict:
    """A raw dict simulating parsed YAML frontmatter for a story spec."""
    return {
        "id": "DIA-001",
        "title": "Define Pydantic models",
        "status": "pending",
        "type": "feature",
        "tags": ["core", "models"],
        "business_value": 500,
        "story_points": 5,
        "parent": "DIA-011",
        "dependencies": [],
        "created": date(2026, 3, 27),
    }


@pytest.fixture
def sample_spec(sample_meta_dict: dict) -> Spec:
    """A fully constructed Spec object for unit tests."""
    return Spec(
        meta=SpecMeta.model_validate(sample_meta_dict),
        body=SpecBody(
            description="Define the canonical Pydantic models.",
            context="Every other module depends on these models.",
        ),
    )


# ---------------------------------------------------------------------------
# Parser fixtures (markdown text strings)
# ---------------------------------------------------------------------------

SAMPLE_SPEC_TEXT = """\
---
id: DIA-001
title: Define Pydantic models
status: pending
type: feature
tags:
  - core
  - models
business_value: 500
story_points: 5
parent: DIA-011
created: 2026-03-27
---

## Description

Define the canonical Pydantic models that every module depends on.

## Context

Every other module imports from core.models. Getting the shape right first prevents churn.

## Behavior

### Scenario: Valid construction

- **Given** a dict with required fields
- **When** SpecMeta.model_validate is called
- **Then** a valid SpecMeta is returned

## Implementation Notes

Chose composition over inheritance for Spec.
"""

MINIMAL_SPEC_TEXT = """\
---
id: DIA-099
title: Minimal spec
type: chore
created: 2026-03-27
---
"""

SPEC_WITH_EXTRAS_TEXT = """\
---
id: DIA-050
title: Spec with custom sections
type: spike
created: 2026-03-27
---

## Description

A spike with custom sections.

## Research Questions

1. How does X work?
2. What are the trade-offs?

## My Custom Section

This is a custom section not in the SpecBody model.

## Another Extra

More custom content here.
"""

EPIC_SPEC_TEXT = """\
---
id: DIA-011
title: Core library epic
type: epic
created: 2026-03-27
---

## Vision

All core modules are implemented and tested.

## Context

The core library is the foundation for MCP and web layers.

## Stories

- [ ] DIA-001: Pydantic models
- [ ] DIA-002: Frontmatter parser
"""

SPIKE_SPEC_TEXT = """\
---
id: DIA-020
title: MCP framework comparison
type: spike
created: 2026-03-27
---

## Description

Compare FastMCP 3.x vs official MCP Python SDK.

## Research Questions

1. Which has better decorator API?
2. Performance comparison?

## Findings

FastMCP has 70% market share and superior DX.

## Recommendation

Use FastMCP 3.x. See ADR-001.
"""


@pytest.fixture
def sample_spec_text() -> str:
    """A complete markdown string with frontmatter + body."""
    return SAMPLE_SPEC_TEXT


@pytest.fixture
def minimal_spec_text() -> str:
    """Frontmatter only, no body sections."""
    return MINIMAL_SPEC_TEXT


@pytest.fixture
def spec_with_extras_text() -> str:
    """Includes unknown sections that should go to extra_sections."""
    return SPEC_WITH_EXTRAS_TEXT


# ---------------------------------------------------------------------------
# Store fixtures
# ---------------------------------------------------------------------------

STORY_TEMPLATE = """\
## Description

<!-- One-line summary -->

## Context

<!-- Why this story exists -->

## Behavior

### Scenario: [name]

- **Given** [precondition]
- **When** [action]
- **Then** [expected outcome]
"""

EPIC_TEMPLATE = """\
## Vision

<!-- End state from the user's perspective -->

## Context

<!-- Strategic goal -->

## Stories

- [ ] ...
"""

SPIKE_TEMPLATE = """\
## Description

<!-- Research question -->

## Research Questions

1. ...

## Findings

## Recommendation
"""


@pytest.fixture
def sample_prefixes() -> dict[str, PrefixDef]:
    """Prefix definitions for store tests."""
    return {
        "DIA": PrefixDef(description="Diatagma core", template="story"),
        "EX": PrefixDef(description="Exploration", template="spike"),
    }


@pytest.fixture
def sample_templates() -> dict[str, str]:
    """Template content keyed by template name."""
    return {
        "story": STORY_TEMPLATE,
        "epic": EPIC_TEMPLATE,
        "spike": SPIKE_TEMPLATE,
    }


@pytest.fixture
def spec_store(tmp_tasks_dir, sample_prefixes, sample_templates) -> SpecStore:
    """A SpecStore pointed at a temporary .tasks/ directory."""
    return SpecStore(
        tasks_dir=tmp_tasks_dir,
        prefixes=sample_prefixes,
        templates=sample_templates,
    )


def seed_spec_file(
    tasks_dir,
    spec_id: str,
    title: str,
    spec_type: str = "feature",
    status: str = "pending",
    **extra_meta,
) -> None:
    """Write a minimal spec file into a directory for testing."""
    ext_map = {"epic": ".epic.md", "spike": ".spike.md"}
    ext = ext_map.get(spec_type, ".story.md")
    slug = title.lower().replace(" ", "-")[:40]
    filename = f"{spec_id}-{slug}{ext}"
    path = tasks_dir / filename

    meta = SpecMeta.model_validate(
        {
            "id": spec_id,
            "title": title,
            "type": spec_type,
            "status": status,
            "created": date(2026, 3, 27),
            **extra_meta,
        }
    )
    spec = Spec(
        meta=meta,
        body=SpecBody(description=f"Description for {spec_id}."),
        file_path=path,
    )
    write_spec_file(spec, path)
