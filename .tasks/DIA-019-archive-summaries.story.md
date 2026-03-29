---
id: DIA-019
title: "Generate context summaries when archiving specs"
status: pending
type: feature
tags: [core, archive, agents]
business_value: 200
story_points: 3
parent: DIA-011
dependencies: [DIA-003, DIA-007]
assignee: ""
created: 2026-03-29
---

## Description

When specs are moved to the archive, auto-generate a concise summary block that preserves key decisions and outcomes without requiring agents to read the full spec.

## Context

Agent context windows are finite and degrade in quality above ~60% utilization. Research on long-running agent sessions consistently shows that success rates drop after 35 minutes, with task duration doubling quadrupling the failure rate. Completed specs accumulate in the archive but still contain valuable context — what was decided, what approach was taken, what was learned. A summary block lets agents reference archived work efficiently without loading full spec bodies. This is the "memory decay" pattern: retain the signal, discard the noise.

The story template already includes an `## Implementation Notes` section where agents append lightweight one-liner notes during development (decisions made, trade-offs, gotchas). These notes are the richest source of "what actually happened" and are the primary input for summary generation. The summary distills Description (what) + Implementation Notes (how/decisions) into a compact block — it doesn't replace or modify either section.

## Behavior

### Scenario: Spec is archived with auto-summary

- **Given** DIA-005 is marked done and has a populated body
- **When** `move_to_archive("DIA-005")` is called
- **Then** a `## Summary` section is prepended to the spec body containing: title, outcome, key decisions, and completion date

### Scenario: Summary is generated from existing content

- **Given** DIA-005 has Description, Context, and Implementation Notes sections
- **When** the summary is generated
- **Then** it extracts: first sentence of Description (the "what"), plus all Implementation Notes entries (the "how/decisions"), plus completion date — into a 3-5 line digest (deterministic, no LLM)

### Scenario: Spec has no implementation notes

- **Given** DIA-005 has a Description but an empty Implementation Notes section
- **When** the summary is generated
- **Then** it uses Description + completion date only (graceful degradation)

### Scenario: Spec already has a summary

- **Given** a spec already contains a `## Summary` section (manually written)
- **When** the spec is archived
- **Then** the existing summary is preserved, not overwritten

## Constraints

- Summaries must be deterministic (no LLM calls) — extract, don't generate
- Summary block must be under 200 words (target: context-efficient)
- Must not modify the original frontmatter
- Archive path: `.tasks/archive/{id}.{type}.md`

## Requirements

- [ ] `generate_summary(spec) -> str` — extract key information from spec body sections
- [ ] Extraction strategy: first sentence of Description + all Implementation Notes entries + completion date
- [ ] Graceful when Implementation Notes is empty (fall back to Description only)
- [ ] Prepend `## Summary` section to body on archive move — full spec body stays intact underneath
- [ ] Skip if `## Summary` already exists
- [ ] Update `move_to_archive` in TaskStore to call summary generation
- [ ] Append archive entry to changelog

## Verification

- [ ] Archived spec has `## Summary` section
- [ ] Summary is under 200 words
- [ ] Existing manually-written summaries are not overwritten
- [ ] Summary content is deterministic (same spec always produces same summary)
- [ ] Changelog records the archive move

## References

- [docs/architecture.md](docs/architecture.md)

## Implementation Notes
