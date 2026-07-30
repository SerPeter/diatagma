---
id: DIA-031
title: Epic propagation, progress, and close nudges
status: pending
type: feature
tags: [cli, dx, lifecycle, epic]
business_value: 400
story_points: 5
created: 2026-07-30
---

## Description

Epics track their children automatically and loudly: MCP status changes trigger the same propagation the CLI already does, epics move to `in-progress` when work starts, an all-children-done event produces a prominent nudge (or announced auto-completion), and `list`/`show`/`validate` surface epic progress instead of hiding it.

## Context

Auto-completion machinery exists (`LifecycleEngine._auto_complete_parents`, default on) but propagation is unreliable in practice for three concrete reasons:

1. **MCP bypasses the lifecycle engine.** `update_spec` and `claim_spec` call `store.update()` directly (`mcp/tools.py:273,292`). An agent marking the last child done *over MCP* triggers no auto-complete, no notice — nothing. Only the CLI `status` path runs propagation. This is the primary cause of "I keep adjusting epics by hand." Fixed foundationally in [[DIA-025]] (routing) and consumed here.
2. **The signal is a whisper.** When auto-complete does fire, it surfaces as one `Auto-completed: DIA-011` line easily lost in output. There is no nudge when auto-complete is *off*, and no upward propagation when work *starts* — an epic sits `pending` while its children are in-progress.
3. **No standing visibility.** `list` shows epics as ordinary rows with no progress; `show <epic>` doesn't list children; `validate` only handles the reverse drift (done epic with active children), never "all children done, epic still open."

## Behavior

### Scenario: MCP completion propagates to the epic

- **Given** epic DIA-011 whose children are all done except DIA-015 (in-progress), `auto_complete_parent` on
- **When** an agent sets DIA-015 `done` via MCP
- **Then** DIA-011 auto-completes AND the MCP response carries an `epic_completed` notice naming DIA-011

### Scenario: all-children-done nudge when auto-complete is off

- **Given** `auto_complete_parent` is false and DIA-011's last non-terminal child is set `done`
- **When** the status change is applied (CLI or MCP)
- **Then** DIA-011 is left unchanged BUT an `epic_ready_to_close` notice is produced: `All 8 children of DIA-011 are done — close it: diatagma status DIA-011 done`

### Scenario: upward propagation on start

- **Given** pending epic DIA-011 with pending child DIA-015, setting `auto_start_parent` on
- **When** DIA-015 moves to `in-progress`
- **Then** DIA-011 moves to `in-progress` and an `epic_started` notice is produced

### Scenario: epic progress in list

- **Given** epic DIA-011 with 3 of 8 children done
- **When** `diatagma list` runs
- **Then** the DIA-011 row shows a progress indicator, e.g. `[3/8]`

### Scenario: child breakdown in show

- **Given** epic DIA-011 with children in mixed states
- **When** `diatagma show DIA-011` runs
- **Then** output includes a children section grouped by status with a `Progress: 3/8 done` summary

### Scenario: validate nudges ready-to-close epics

- **Given** an active epic whose children are all terminal but the epic is not (e.g. frontmatter edited out of band)
- **When** `diatagma validate` runs
- **Then** an `epic_ready_to_close` issue is reported (nudge, not auto-corrected)

## Constraints

- Recursion stays safe: nested epics propagate upward without double-processing (existing `_auto_complete_parents` recursion is the model).
- `cancelled` counts as terminal for "all children done" (matches `_TERMINAL_STATUSES`); an all-cancelled epic nudges to `cancelled`, not `done` — or simply surfaces the state without prescribing.
- Upward-start propagation is opt-in via a new `auto_start_parent` setting (default on) so teams that model epics differently can disable it.
- Notices reuse the [[DIA-025]] channel; no bespoke print paths.
- No behavior change to a spec with no parent.

## Verification

- [ ] Lifecycle tests: MCP-routed completion auto-completes the epic; nudge when auto-complete off
- [ ] Upward-start propagation test with the setting on/off
- [ ] `list` progress indicator and `show` children breakdown tests
- [ ] `validate` `epic_ready_to_close` test
- [ ] MCP `update_spec`/`claim_spec` return epic notices (depends on [[DIA-025]] routing)
- [ ] Full suite, ruff, ty pass

## References

- [[DIA-021]] lifecycle automation, [[DIA-025]] notice channel + MCP routing, [[DIA-013]] web dashboard epic, [[DIA-029]] archive propagation

## Additional workflow ideas (not yet scoped)

- `diatagma epics` — dedicated listing of epics with progress bars and blocked-child flags.
- Archive an epic and its terminal children together (`archive DIA-011` cascades) — ties to [[DIA-029]].
- Roadmap already renders an epics table; link its rows to these nudges.
- Epic health in `next`: deprioritize starting new epics while others are near-done.

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

## Implementation Notes
