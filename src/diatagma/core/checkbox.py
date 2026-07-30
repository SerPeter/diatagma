"""Checkbox progress parsing for spec bodies.

Counts GitHub-style task-list items (``- [ ]`` / ``- [x]``) in a spec's
markdown body, excluding template placeholder stubs like ``- [ ] ...``.
The Verification section's boxes are the "done" contract; this lets the
lifecycle warn when a spec is completed with work still unchecked.
"""

from __future__ import annotations

import re

from diatagma.core.models import Spec

_CHECKBOX_RE = re.compile(r"^[ \t]*[-*][ \t]+\[([ xX])\][ \t]+(.*)$", re.MULTILINE)
"""Matches a task-list item, capturing the mark and the label text.

Whitespace classes are horizontal-only (``[ \\t]``) so an empty-label box
like ``- [ ]`` cannot swallow the following line as its label.
"""


def _is_placeholder(label: str) -> bool:
    """True for the template stub ``- [ ] ...`` (or an empty label)."""
    stripped = label.strip()
    return not stripped or stripped == "..."


def count_checkboxes(text: str | None) -> tuple[int, int]:
    """Return ``(checked, total)`` task-list items, ignoring placeholders."""
    if not text:
        return (0, 0)
    checked = 0
    total = 0
    for mark, label in _CHECKBOX_RE.findall(text):
        if _is_placeholder(label):
            continue
        total += 1
        if mark in ("x", "X"):
            checked += 1
    return (checked, total)


def checkbox_progress(spec: Spec) -> tuple[int, int]:
    """Return ``(checked, total)`` for a spec, preferring its raw body."""
    text = spec.raw_body
    if text is None:
        from diatagma.core.parser import _render_body

        text = _render_body(spec.body)
    return count_checkboxes(text)


__all__ = ["checkbox_progress", "count_checkboxes"]
