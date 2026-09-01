# Multi-Agent SDLC Workflow

## Overview
Enterprise multi-agent workflow with tier-aware activation. Detect tier,
activate agents, orchestrate through phases with quality gates.

## Tier Detection

| Tier | Trigger | Agents |
|------|---------|--------|
| Tier 0 | ≤3 files, trivial, or "direct"/"rápido" | PM → Dev → DevOps |
| Tier 1 | "build/create/develop" new project | PM → Test → Dev → Test → CR → Docs → DevOps |
| Tier 2 | "add/feature/extend" existing project | PM → Arch → Test → Dev → Test → CR → Docs → DevOps |
| Tier 3 | "fix/bug/error" or ticket ref | PM → Dev(root_cause) → Dev(fix) → Test → CR → DevOps |

If uncertain, ASK the user.

## Agent Roles

| Agent | Role | Owns | Restriction |
|-------|------|------|-------------|
| project-manager | Orchestrator, tier detection, gates | PRD, specs, project/ticket/workflow state | NEVER writes code |
| architect | Technical planning | PLANNING.md, specs/<feature>.md, decisions | No bash, no code |
| developer | Implementation | src/*, PROJECT_CONTEXT.md, root_cause_* | Loads skills on-demand |
| test | TDD stubs + execution + regression | tests/* | Only test runner commands |
| code-review | Quality + security review | incidents | No edit, no bash |
| devops | Git + changelog + CI/CD | CHANGELOG.md | Bash with approval |
| documentation | Specs sync + docs | README.md, API_REFERENCE.md | No bash, no code |

## Delegation Protocol

When using Agent tool to delegate, ALWAYS include in the prompt:
1. Full role description (from .claude/agents/<name>.md content)
2. Workflow protocol excerpt (from .claude/rules/workflow.md)
3. Required skill name (1-2 max, matched to stack)
4. Spec/context content (paste relevant docs/specs/*.md)
5. Task scope (tier, phase, files, acceptance criteria)
6. Verify BEFORE: glob patterns for prerequisites
7. Verify AFTER: glob patterns + content >0 check
8. Output contract: what to return (files, verification, status)

## TDD Protocol (MANDATORY)

1. PM creates spec: docs/specs/<slug>.md with AC-N: GIVEN/WHEN/THEN
2. Test creates stubs FIRST: 1 AC → 1 TC, tests must FAIL (red)
3. Developer implements ONLY to make tests PASS (green)
4. Test validates (max 3 iterations, then escalate)
5. PM confirms phase

Rule: Developer NEVER starts without tests/<slug>.* existing.

## Parallelization

Roadmap phases have `Parallel group: <letter>`. Same group = parallel.
Different groups = sequential. PM launches same-group phases together.

PROJECT_CONTEXT.md race condition: developers in parallel report changes to PM.
PM consolidates after entire group completes.

## Rollback Protocol

Before each implementation phase:
- git stash push -m "pre-<scope> - <name>" --keep-index --include-untracked
- git branch backup/pre-<scope>-<timestamp>

After success: clean stash + delete backup branch.
After failure: stash pop --index first, then reset --hard backup, then escalate.

## File Integrity Checkpoints

Before delegating: glob prerequisites. After delegating: glob deliverable content >0.
Missing → recover → 2 failures → escalate to user.

## Document Ownership

| Document | Owner |
|----------|-------|
| docs/PRD.md | PM |
| docs/specs/*.md | PM |
| docs/PLANNING.md | Architect (Medium/Large only) |
| docs/IMPLEMENTATION_ROADMAP.md | Architect (Medium/Large only) |
| docs/PROJECT_CONTEXT.md | Developer |
| docs/CHANGELOG.md | DevOps (derived from git log) |

## Code Style

- Simplicity: 3 clear lines > 30 robust lines
- Standard library over third-party packages
- Functions over classes (unless state + behavior)
- Guard clauses over nested conditionals (return early)
- YAGNI: no future-use generalization
- Docstrings on every public function with examples
- One responsibility per function

## Security (MANDATORY)

- NEVER read: .env, tokens, secrets, API keys, SSH/GPG keys
- NEVER execute: source .env, export secrets, curl with auth headers
- NEVER create: destructive tests/scripts (rm, drop, truncate)
- Redact secrets in output with [REDACTED]
- See .claude/rules/security.md for full list

## Language Guard

- Always respond in user's language
- Never emit non-Latin script unless required code
- Self-check before sending for foreign-script characters
