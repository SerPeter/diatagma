# ADR-004: Status vocabulary is config-driven, not hardcoded

## Status

Accepted

## Context

Spec statuses (`pending`, `in-progress`, `done`, …) are declared in
`settings.yaml` and are meant to be customizable per project. But the code that
reasoned about statuses embedded the vocabulary as string literals in ~30
places across 7 modules: `{done, cancelled}` for "is this terminal?" and
`{in-progress, in-review}` / `"in-progress"` for "is work underway?".

This coupling was invisible under the default config, where the literals happen
to equal the configured values — so the full test suite passed while a project
that renamed `done` to `complete` (a supported customization) would silently
break: blocking treated a completed blocker as still-blocking, the roadmap
mis-counted, epics auto-completed to an out-of-config status, `drift` stopped
flagging stale work, and completion warnings disappeared. An adversarial review
reproduced every one of these against a renamed `settings.yaml`.

## Decision

The status vocabulary is owned by configuration; no module hardcodes a status
literal in logic. `Settings` exposes the vocabulary and its lifecycle roles:

- `terminal_statuses` (config) → `terminal_status_set` — statuses that count as
  finished/closed. Drives all blocking and lifecycle "is terminal" checks.
- `active_statuses` (config) → `active_status_set` — statuses that count as work
  in flight. Drives the roadmap Active column, epic auto-start, and drift
  staleness.
- `started_status` = `active_statuses[0]` — the status a parent epic is promoted
  to when a child begins work.
- `completed_status` = `terminal_statuses[0]` — the successful-completion status;
  used when auto-completing a parent and when deciding whether a completion
  should warn about unchecked verification boxes (distinct from a cancellation
  terminal status).

**Convention: order is significant.** The first entry of `active_statuses` is
"started" and the first of `terminal_statuses` is "completed (success)". Any new
code that reasons about status membership or transitions reads from `Settings`;
it must never compare against a literal like `"done"` or `"in-progress"`.

`SpecGraph` carries the terminal set (passed at `build()` from config via
`refresh_graph`) so blocking queries need no per-call threading. Two single-spec
semantic checks are intentionally *not* generalized and are documented as such:
the auto-start guard requires the parent to be exactly `pending` (only a
not-started parent is promoted — a `blocked` one is left alone), and the
`started`/`completed` roles use position, not a separate config field.

## Consequences

### Positive

- Renaming or adding statuses in `settings.yaml` "just works" across blocking,
  lifecycle, roadmap, drift, and the graph.
- One source of truth removes a class of silent-divergence bugs.

### Negative

- The `[0]` positional convention for `started`/`completed` is implicit; a
  project that lists its terminal statuses cancellation-first would mislabel the
  completed status. Documented, not validated.

### Neutral

- Status strings are still free-form on write (`SpecMeta.status: str`); the
  config is authoritative for *interpretation*, not for validating what gets
  written. A future `validate` check could flag out-of-vocabulary statuses.

## References

- Archived specs DIA-025, DIA-028, DIA-031 (features that consume these roles)
- Settings: `src/diatagma/core/models.py`
