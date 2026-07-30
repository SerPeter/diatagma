"""Status drift detection — compare recorded spec status against git history.

Read-only. Two kinds of drift are reported:

- ``implemented_not_marked`` — a non-terminal spec whose ID is referenced by a
  commit message (work was committed but ``diatagma status ... done`` skipped).
- ``stale_in_progress`` — an in-progress spec whose file hasn't been touched by
  a commit within ``stale_days``.

Git is invoked via subprocess; if it is unavailable the functions degrade to
empty results rather than raising, and :func:`git_available` lets callers warn.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from diatagma.core.models import Spec

_SPEC_ID_RE = re.compile(r"\b[A-Z]{1,5}-\d{3,}\b")
_TERMINAL_STATUSES = frozenset({"done", "cancelled"})


@dataclass(frozen=True)
class DriftRecord:
    """A single detected disagreement between spec status and git history."""

    spec_id: str
    kind: str
    detail: str


def _git(args: list[str], cwd: Path) -> str | None:
    """Run a git command; return stdout, or None on any failure."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_available(repo_root: Path) -> bool:
    """True if *repo_root* is inside a usable git working tree."""
    return _git(["rev-parse", "--is-inside-work-tree"], repo_root) is not None


def _commits_mentioning_specs(repo_root: Path) -> dict[str, list[str]]:
    """Map each spec ID to short hashes of commits whose SUBJECT mentions it.

    Only the subject line is scanned, not the body. Under this repo's
    conventional-commit convention the ID of the work being done rides in the
    subject (``feat(x): thing (DIA-042)``); bodies routinely list many IDs for
    context (spec-file edits, epic child lists, "added notes to DIA-009,
    DIA-010"), which would otherwise produce false-positive drift.
    """
    log = _git(["log", "--format=%h%x1f%s%x1e"], repo_root)
    if not log:
        return {}
    mentions: dict[str, list[str]] = {}
    for record in log.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        short, _, subject = record.partition("\x1f")
        for spec_id in set(_SPEC_ID_RE.findall(subject)):
            mentions.setdefault(spec_id, []).append(short)
    return mentions


def _last_commit_date(path: Path, repo_root: Path) -> date | None:
    """Committer date (YYYY-MM-DD) of the last commit touching *path*."""
    out = _git(["log", "-1", "--format=%cs", "--", str(path)], repo_root)
    if not out or not out.strip():
        return None
    try:
        return date.fromisoformat(out.strip())
    except ValueError:
        return None


def detect_drift(
    specs: list[Spec],
    repo_root: Path,
    *,
    today: date,
    stale_days: int = 14,
) -> list[DriftRecord]:
    """Return drift records for the given specs against git history."""
    records: list[DriftRecord] = []
    mentions = _commits_mentioning_specs(repo_root)

    for spec in specs:
        if spec.meta.status in _TERMINAL_STATUSES:
            continue

        commits = mentions.get(spec.meta.id, [])
        if commits:
            shown = ", ".join(commits[:5])
            records.append(
                DriftRecord(
                    spec_id=spec.meta.id,
                    kind="implemented_not_marked",
                    detail=f"{spec.meta.status}, but referenced in commits: {shown}",
                )
            )

        if spec.meta.status == "in-progress" and spec.file_path is not None:
            last = _last_commit_date(spec.file_path, repo_root)
            if last is not None:
                age = (today - last).days
                if age > stale_days:
                    records.append(
                        DriftRecord(
                            spec_id=spec.meta.id,
                            kind="stale_in_progress",
                            detail=f"in-progress with no commits touching it in {age} days",
                        )
                    )

    return records


__all__ = ["DriftRecord", "detect_drift", "git_available"]
