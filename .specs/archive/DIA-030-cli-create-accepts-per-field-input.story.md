---
id: DIA-030
title: CLI create accepts per-field input
status: done
type: feature
tags: [cli, dx]
business_value: 200
story_points: 3
created: 2026-07-30
updated: 2026-07-30
---

## Description

`diatagma create` accepts options for frontmatter and body fields — `--business-value`, `--story-points`, `--tags`, `--parent`, `--cycle`, `--assignee`, `--description`, and repeatable `--verification` — so a spec is generated with its metadata and key sections already filled, instead of an empty template the agent must re-open and edit.

## Context

`create` currently takes only `title`, `--type`, `--prefix`; everything else is a follow-up `edit`. Agents routinely know the business value, parent epic, and acceptance criteria at creation time. Passing them up front produces a ready-to-work spec in one call and cuts the "create then edit" round-trip. Frontmatter fields ride the `**meta` path already merged in `store.create` ([[DIA-016]] frontmatter fix); body fields fill their template sections.

## Behavior

### Scenario: frontmatter fields set at creation

- **Given** `diatagma create "Thing" --business-value 300 --story-points 5 --parent DIA-011 --tags cli,dx`
- **When** the spec is created
- **Then** its frontmatter carries `business_value: 300`, `story_points: 5`, `parent: DIA-011`, `tags: [cli, dx]`

### Scenario: description fills the Description section

- **Given** `diatagma create "Thing" --description "Users can do X"`
- **When** the spec is created
- **Then** the `## Description` section contains `Users can do X` in place of the placeholder comment

### Scenario: repeatable verification items become checkboxes

- **Given** `diatagma create "Thing" --verification "does A" --verification "does B"`
- **When** the spec is created
- **Then** the `## Verification` section lists `- [ ] does A` and `- [ ] does B`, replacing the `- [ ] ...` stub

### Scenario: omitted fields keep template defaults

- **Given** `diatagma create "Thing"` with no field options
- **When** the spec is created
- **Then** behavior is identical to today (template defaults, placeholder sections intact)

### Scenario: guards still apply

- **Given** `--parent` points at an archived epic
- **When** create runs without `--reopen`
- **Then** the existing `LifecycleError` guard fires (unchanged)

### Scenario: MCP create parity

- **Given** the MCP `create_spec` tool
- **When** it is called with description/verification
- **Then** the same body-filling behavior applies (shared core helper)

## Constraints

- Body filling is surgical: replace the target section's placeholder while preserving the rest of the template (other sections, comments).
- Field validation reuses `SpecMeta` (e.g. `story_points` restricted to the Fibonacci set) — invalid values fail with a clear CLI error, not a traceback.
- `--tags` accepts comma-separated or repeated; normalize to a list.
- No change to the generated file when no field options are supplied.

## Verification

- [x] CLI tests for each field option and combinations
- [x] Section-fill helper unit tests (description, verification, preserves siblings)
- [x] Invalid `--story-points` rejected with friendly error
- [x] MCP `create_spec` parity test
- [x] Full suite, ruff, ty pass

## References

- [[DIA-016]] template frontmatter merge, [[DIA-020]] CLI

---
<!-- ═══ Fill during/after implementation ═══ -->

## Implementation Summary

`diatagma create` gained `--business-value`, `--story-points`, `--tags`,
`--parent`, `--cycle`, `--assignee`, `--description`, and repeatable
`--verification`. Frontmatter fields ride the `**meta` path into `store.create`
(building on the [[DIA-016]] merge); body fields are filled surgically by a new
`parser.fill_body_sections` helper that replaces a section's placeholder while
preserving every other section and its comments. `store.create` pops
body-section keys out of the metadata before frontmatter validation and fills
them into the resolved template. MCP `create_spec` gained matching
`description`/`verification` params (newline-separated criteria) via the same
core path.

## Implementation Notes

- `--verification` items are formatted into `- [ ]` checkboxes by the CLI; MCP
  takes newline-separated criteria and does the same.
- Invalid `--story-points` (non-Fibonacci) surfaces as a clean CLI error via the
  existing `SpecMeta` validation + `print_error`, no traceback.
- A missing target section is appended rather than dropped, so body fields work
  regardless of the template's section set.
