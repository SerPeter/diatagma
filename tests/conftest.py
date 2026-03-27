"""Shared test fixtures.

Provides:
    tmp_tasks_dir   — a temporary .tasks/ directory with config and sample specs
    sample_meta_dict — a raw dict simulating parsed YAML frontmatter
    sample_spec     — a parsed Spec object for unit tests
    spec_store      — a SpecStore pointed at tmp_tasks_dir
"""

from datetime import date

import pytest

from diatagma.core.models import Spec, SpecBody, SpecMeta


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
