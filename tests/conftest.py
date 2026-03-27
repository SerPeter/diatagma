"""Shared test fixtures.

Provides:
    tmp_tasks_dir  — a temporary .tasks/ directory with config and sample tasks
    sample_task    — a parsed Task object for unit tests
    task_store     — a TaskStore pointed at tmp_tasks_dir
"""

import pytest


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
