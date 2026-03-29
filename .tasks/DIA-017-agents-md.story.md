---
id: DIA-017
title: "Establish AGENTS.md as canonical agent instructions, CLAUDE.md as pointer, and CLI skill"
status: pending
type: feature
tags: [cli, agents, dx]
business_value: 300
story_points: 5
parent: DIA-012
dependencies: [DIA-008, DIA-015, DIA-020]
assignee: ""
created: 2026-03-29
updated: 2026-03-29
---

## Description

Make AGENTS.md the single source of truth for agent instructions (replacing CLAUDE.md's current role), auto-generate it from project config, reduce CLAUDE.md to a pointer, and provide a CLI skill so agents without MCP access still know how to use diatagma.

## Context

A growing standard in the developer tooling ecosystem is placing an AGENTS.md file at the repo root — a "README for AI agents" that describes build commands, architecture, coding conventions, and boundaries. Over 20,000 repositories now use this convention, and major AI coding tools recognize it automatically. Meanwhile, CLAUDE.md is Claude-specific and currently contains project instructions that should be universal across all agents.

The right structure is: AGENTS.md holds all agent-relevant project knowledge (auto-generated sections from diatagma config + manually maintained project sections), and CLAUDE.md becomes a thin file that points to AGENTS.md plus any Claude-specific configuration. This way, Cursor, Copilot, Roo Code, Cline, and any future agent all get the same instructions.

Additionally, agents that connect via shell (not MCP) need a way to learn the CLI. A Claude Code skill (invocable via slash command) teaches the agent the full CLI interface so it can use `diatagma ready`, `diatagma status`, etc. without needing MCP tools.

## Behavior

### Scenario: Generate AGENTS.md for a new project

- **Given** a diatagma project with configured prefixes, statuses, and templates
- **When** `diatagma agents-md` is run
- **Then** an AGENTS.md file is written to the repo root with project-specific agent instructions including: prefixes, statuses, spec types, CLI commands, workflow, and boundaries

### Scenario: Existing CLAUDE.md content migrated

- **Given** CLAUDE.md contains project instructions (architecture, conventions, etc.)
- **When** the migration is performed
- **Then** universal agent instructions move to AGENTS.md, CLAUDE.md is reduced to a pointer (`See @AGENTS.md for project instructions`) plus any Claude-specific config (hooks, model preferences, etc.)

### Scenario: Regenerate after config change

- **Given** AGENTS.md exists with auto-generated and user-maintained sections
- **When** `diatagma agents-md` is run after adding a new prefix to `prefixes.yaml`
- **Then** the auto-generated section is updated to include the new prefix; user-maintained sections are preserved

### Scenario: Agent uses CLI skill (no MCP)

- **Given** an agent has shell access but no MCP connection to diatagma
- **When** the user or agent invokes the `/diatagma` skill
- **Then** the agent receives full CLI reference: available commands, common workflows (find ready work, claim spec, update status), and output format options

### Scenario: Content includes actionable instructions

- **Given** a generated AGENTS.md
- **When** an AI agent reads it
- **Then** the agent knows: available prefixes, status workflow, how to find ready work via CLI or MCP, how to claim specs, and project boundaries

## Constraints

- Auto-generated section of AGENTS.md must be under 150 lines (agent context efficiency)
- Must be deterministic: same config always produces same output
- Should not overwrite user content — use fenced auto-generated sections with markers
- CLAUDE.md must remain functional for Claude Code (it still loads this file automatically)
- CLI skill must be a standalone `.md` file that can be registered in Claude Code settings

## Requirements

### AGENTS.md Generation
- [ ] `generate_agents_md(config, output_path)` in core
- [ ] Auto-generated section within `<!-- diatagma:start -->` / `<!-- diatagma:end -->` markers
- [ ] Auto-generated content includes: project overview, prefixes with descriptions, status values, spec types, CLI commands reference, MCP tools reference, workflow (find ready -> claim -> work -> update -> complete), boundaries
- [ ] Preserve all user content outside the fenced markers
- [ ] CLI command: `diatagma agents-md`

### CLAUDE.md Migration
- [ ] Migrate universal project instructions from current CLAUDE.md into AGENTS.md (manually maintained section, outside the markers)
- [ ] Reduce CLAUDE.md to: pointer to AGENTS.md (`See @AGENTS.md`), plus Claude-specific configuration only (hooks, model preferences, permission settings)

### CLI Skill
- [ ] Create `.claude/skills/diatagma.md` skill file
- [ ] Content: full CLI command reference with examples, common workflows, output format options (`--json`, `--quiet`)
- [ ] Invocable as `/diatagma` in Claude Code
- [ ] Should be generated/updated by `diatagma agents-md --skill` to stay in sync with actual CLI commands

## Verification

- [ ] Generated AGENTS.md auto-section is valid markdown under 150 lines
- [ ] Includes all configured prefixes and statuses
- [ ] Regeneration preserves user content outside markers
- [ ] Deterministic: same config produces identical output
- [ ] CLAUDE.md points to AGENTS.md and Claude Code still loads project context
- [ ] `/diatagma` skill is invocable and provides accurate CLI reference
- [ ] Agent without MCP can complete full workflow using only CLI commands from the skill

## References

- [AGENTS.md standard](https://agents.md/)

## Implementation Notes
