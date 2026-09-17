# Multi-Layer Integration of the Project

## System layers

| Layer | File | Content | Status |
|------|------|---------|--------|
| **1. Base identity** | `CLAUDE.md` | DOGMAS CORE v4.1 + security + agent roles | ✅ Complete |
| **2. Security** | `.claude/rules/security.md` + settings.json | Complete security policy + 26 deny patterns + hooks | ✅ Complete |
| **3. Tools** | `.claude/agents/*.md` (7 agents) | PM, Architect, Developer, Test, Code Review, DevOps, Documentation | ✅ Complete |
| **4. Model** | `Agent tool` (subagent_type) | Inherited by subagents; CORE + rules | ✅ Automatic inheritance |
| **5. Project instructions** | `.claude/rules/workflow.md` + CLAUDE.md | Workflow protocol + tier detection + TDD + formalization | ✅ Complete |
| **6. Memory** | `openspec/` + `MEMORY/` + `eval/` | Specs, design, tasks, cases, evaluation, crystallized memory | ✅ Complete |

## Implemented hooks

| Hook | Event | Function |
|------|-------|----------|
| `format-after-edit.sh` | PostToolUse (Write/Edit) | Automatic formatting |
| `audit-log.sh` | PostToolUse (Write/Edit/Bash) | Event recording |
| `redact-output.py` | PostToolUse (Bash) | Secret redaction |
| `scope-validator.sh` | Stop | heartbeat `Scope:` + `Security:` |
| `phase-gate.sh` | UserPromptSubmit | Phase-integrity gate |
| PreToolUse inline | PreToolUse (Bash) | Blocks irreversible actions |

## Task status

- **Completed:** 92
- **Partial (design complete, execution pending):** 26
- **Pending (blocked by infrastructure):** 1 (general reference, not specific)
