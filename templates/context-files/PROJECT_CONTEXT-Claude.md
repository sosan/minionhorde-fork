# Project Context (Claude Adaptation — GENERATED from templates/context-files/PROJECT_CONTEXT.md)

> **GENERATED FILE — Source: `templates/context-files/PROJECT_CONTEXT.md` (OpenCode).**
> **Adapted for Claude:** Same structure. In Claude, this file is the living project state that Developer updates after each phase and PM consolidates after parallel groups. Memory MCP `implementation_*` entities complement it if MCP enabled.**

# Project Context

## Last Updated: {{TIMESTAMP}}
## Current Phase: {{PHASE_NAME}}
## Active Workflow Mode: {{new-project | add-feature | fix-bug | direct-response}}

## Project Summary
{{2-3 lines describing what this project is and its current state}}

## Tech Stack
- {{framework}}: {{version}}
- {{database}}: {{version}}
- ...

## Current File Structure
```
{{tree of relevant files — only show src/, tests/, docs/ and key config files}}
```

## Recent Changes
| Date | Phase | Files Changed | Description |
|------|-------|---------------|-------------|
| {{YYYY-MM-DD}} | {{Phase N}} | {{file1, file2}} | {{brief description}} |

## Open Items
- [ ] {{Item 1 — what needs to be done}}
- [x] {{Item 2 — resolved in Phase N}}

## Known Issues
- None / or list — sourced from incident_* entities if Memory MCP enabled, or manual:
  - {{issue reference — severity, file:line, description}}

## Workflow Link (Claude-specific)

- **Source of truth for structure:** `.claude/rules/workflow.md` (adapted from `rules/workflow-protocols.md`)
- **Agents:** `.claude/agents/*.md` (adapted from `agents/*.md`)
- **In OpenCode:** `agents/*.md`, `rules/workflow-protocols.md`, `AGENTS.md` are SSOT — this file mirrors `docs/PROJECT_CONTEXT.md` in both systems
