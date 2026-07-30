"""Tests for core.drift — status drift detection over git history."""

import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from diatagma.core.drift import detect_drift, git_available
from diatagma.core.models import Spec, SpecMeta


def _run(args: list[str], cwd: Path, env: dict | None = None) -> None:
    subprocess.run(
        args, cwd=str(cwd), check=True, capture_output=True, text=True, env=env
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "t@t.io"], tmp_path)
    _run(["git", "config", "user.name", "Test"], tmp_path)
    return tmp_path


def _spec(spec_id: str, status: str = "pending", file_path: Path | None = None) -> Spec:
    return Spec(
        meta=SpecMeta(
            id=spec_id,
            title=spec_id,
            type="feature",
            status=status,
            created=date(2026, 3, 27),
        ),
        file_path=file_path,
    )


def _commit(repo: Path, message: str, filename: str = "f.txt", when: str | None = None):
    (repo / filename).write_text("x", encoding="utf-8")
    _run(["git", "add", "-A"], repo)
    env = None
    if when is not None:
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    _run(["git", "commit", "-m", message], repo, env=env)


class TestGitAvailable:
    def test_true_in_repo(self, git_repo: Path):
        assert git_available(git_repo) is True

    def test_false_outside_repo(self, tmp_path: Path):
        assert git_available(tmp_path) is False


class TestDetectDrift:
    def test_implemented_not_marked(self, git_repo: Path):
        _commit(git_repo, "feat(core): add thing (DIA-001)")
        records = detect_drift(
            [_spec("DIA-001", status="in-progress")],
            git_repo,
            today=date(2026, 7, 30),
        )
        assert any(r.kind == "implemented_not_marked" for r in records)

    def test_no_drift_when_done(self, git_repo: Path):
        _commit(git_repo, "feat: add thing (DIA-001)")
        records = detect_drift(
            [_spec("DIA-001", status="done")], git_repo, today=date(2026, 7, 30)
        )
        assert records == []

    def test_body_only_mention_is_not_drift(self, git_repo: Path):
        # Regression: incidental spec-ID mentions in the commit BODY (e.g. a
        # commit that edits the spec file or lists epic children) must not be
        # read as "implemented". Only the subject counts.
        _commit(
            git_repo,
            "docs(specs): rework specs\n\nAdded notes to DIA-001 and DIA-002.",
        )
        records = detect_drift(
            [_spec("DIA-001", status="pending"), _spec("DIA-002", status="pending")],
            git_repo,
            today=date(2026, 7, 30),
        )
        assert records == []

    def test_clean_repo_no_drift(self, git_repo: Path):
        _commit(git_repo, "chore: unrelated commit")
        records = detect_drift(
            [_spec("DIA-001", status="pending")], git_repo, today=date(2026, 7, 30)
        )
        assert records == []

    def test_stale_in_progress(self, git_repo: Path):
        specfile = git_repo / "DIA-002-x.story.md"
        specfile.write_text("---\nid: DIA-002\n---\n", encoding="utf-8")
        _commit(
            git_repo,
            "add spec DIA-002",
            filename="DIA-002-x.story.md",
            when="2026-01-01T00:00:00",
        )
        records = detect_drift(
            [_spec("DIA-002", status="in-progress", file_path=specfile)],
            git_repo,
            today=date(2026, 7, 30),
            stale_days=14,
        )
        assert any(r.kind == "stale_in_progress" for r in records)

    def test_not_stale_within_threshold(self, git_repo: Path):
        specfile = git_repo / "DIA-003-x.story.md"
        specfile.write_text("---\nid: DIA-003\n---\n", encoding="utf-8")
        _commit(
            git_repo,
            "add spec DIA-003",
            filename="DIA-003-x.story.md",
            when="2026-07-25T00:00:00",
        )
        records = detect_drift(
            [_spec("DIA-003", status="in-progress", file_path=specfile)],
            git_repo,
            today=date(2026, 7, 30),
            stale_days=14,
        )
        assert not any(r.kind == "stale_in_progress" for r in records)

    def test_git_unavailable_returns_empty(self, tmp_path: Path):
        records = detect_drift(
            [_spec("DIA-001", status="in-progress")],
            tmp_path,
            today=date(2026, 7, 30),
        )
        assert records == []
