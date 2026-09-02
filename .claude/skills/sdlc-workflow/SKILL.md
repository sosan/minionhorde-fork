# SDLC Multi-Agent Workflow Skill (Claude Adaptation — GENERATED from .claude/skills/sdlc-workflow/SKILL.md + agents/project-manager.md + rules/workflow-protocols.md)

> **GENERATED FILE — Source: `rules/workflow-protocols.md` (OpenCode SSOT) adapted for Claude Code Agent tool.**
> **Do not edit directly — derived from OpenCode SSOT. Tool mapping: `task` → `Agent`, `read/glob/grep` → `Read/Glob/Grep`, `question` → `AskUserQuestion`, `todowrite` → `TodoWrite`.**

## When to Use

When the user says "build me...", "create a project", "add a feature", "fix this bug", "start the workflow", "run the pipeline", or any development task that benefits from structured SDLC with tier-aware activation and quality gates.

## Workflow Overview

### Phase 0: Detect & Assess

1. Detect tier from user request (see `.claude/rules/workflow.md` Tier Detection + `.claude/agents/project-manager.md` Mode Detection)
   - `create/build/develop` → Tier 1 (new-project)
   - `add/feature/extend` on existing project → Tier 2 (feature addition)
   - `fix/bug/error` or `#ticket` → Tier 3 (bug fix)
   - `≤3 files`, trivial, or flag `direct/rápido/sin pipeline` → Tier 0 (direct)
2. If uncertain, ASK via AskUserQuestion (never guess)
3. Ask complexity questions (modules, services, testing level) per tier — see project-manager.md Complexity Assessment
4. Determine agent activation per matrix (Small/Medium/Large + risk Low/Medium/High) — see workflow.md Document Ownership Map pruning
5. Create feature branch via DevOps Agent: `feature/<slug>` (Tier1), `feature/<feature-slug>` (Tier2), `fix/<ticket>-<desc>` (Tier3), `direct/<desc>` (Tier0)
6. If Memory MCP enabled, create `workflow_*` entity with `start_time`, `tier`, `feature`; else track in `docs/PROJECT_CONTEXT.md` + TodoWrite

### Phase 1: Requirements (PM direct — Tier 1 only, Tier 0 skips)

1. PM creates `docs/PRD.md` using `templates/context-files/PRD-Claude.md` template
2. PM creates `docs/specs/<slug>.md` per functionality using `templates/context-files/SPEC-Claude.md` (GIVEN/WHEN/THEN AC-N + §2 Domain Terms + §3 Dependencies + §8 NFR + §9 AC-N + §10 Test Mapping scaffold)
3. Verify: Glob `docs/PRD.md` + Glob `docs/specs/*` → content >0 (File Integrity Checkpoint 1-A)

### Phase 1b: TDD Stubs (Test Agent via Agent, per spec — MANDATORY before Developer)

1. For each spec: delegate to Test Agent via Agent tool with Delegation Prompt Template
2. Test reads spec AC-N (§9), creates `tests/<slug>.*` with 1 AC → 1 TC-00N mapping, updates spec §10 Test Scenarios Mapping + Traceability
3. Tests must initially FAIL (red phase) — no source yet; coverage 100% AC→TC before Developer starts
4. Verify: Glob `tests/<slug>.*` + content >0 + §10 coverage 100% (Checkpoint 1b-B)
5. Repeat Phase 1b for each spec before Phase 2

### Phase 2: Planning (Architect via Agent — Tier 1 Medium/Large only)

1. Tier 1 Small / Tier 0: **SKIP** — no PLANNING.md / ROADMAP, no gates. Jump 1b → 3.
2. Tier 1 Medium/Large: delegate to Architect via Agent → `docs/PLANNING.md` (tech stack, decisions AD-N, component boundaries, data flow, scalability) + `docs/IMPLEMENTATION_ROADMAP.md` with `Parallel group: <letter>` + `status: pending/in_progress/done` per phase + dependencies
3. Verify: Glob `docs/PLANNING.md` + Glob `docs/IMPLEMENTATION_ROADMAP.md` → content >0 (Checkpoints 2-A/B)

### Phase 3: Implementation (Developer via Agent, TDD) — Parallel-group aware

1. Group phases by `Parallel group` markers in ROADMAP (A, B, C…); without marker → sequential
2. For EACH group in order A→B→C:
   a. **Safety nets:** Delegate to DevOps via Agent → `git stash push -m "pre-group-<letter> - <names>" --keep-index --include-untracked` + `git branch backup/pre-group-<letter>-<timestamp>` → verify both via `git branch --list` + `git stash list` (see workflow.md §Rollback Protocol §Naming Convention `pre-<scope>` unificado)
   b. **Verify tests exist** for ALL phases in group — Glob `tests/<slug>.*` per phase → if any missing delegate Test first (do NOT start group)
   c. **Delegate Developer(s) IN PARALLEL (single message, N Agent calls):** one `Agent(subagent_type="developer")` per phase in group, each with Delegation Prompt Template. **Parallel Developers MUST NOT write docs/PROJECT_CONTEXT.md** — they report delta to PM
   d. Wait ALL in group to complete. **PM consolidates docs/PROJECT_CONTEXT.md** from reports (single write)
   e. Checkpoint 3-B: verify src files for group + consolidated PROJECT_CONTEXT.md >0
   f. **Test validates per phase** (can be parallel if tests disjoint) — max 3 iterations per phase via PM→Developer→Test loop (workflow.md §TDD Protocol + AGENTS.md feedback loop)
   g. On PASS for all phases in group: delegate DevOps to clean `git stash drop stash@{0}` + `git branch -d backup/pre-group-<letter>-*` → verify cleaned
   h. On FAIL after max iter: follow workflow.md §Rollback Protocol (stash pop → backup branch → escalate) — do NOT advance to next group
3. For non-parallel (sequential) tiers (Tier2 Phase2, Tier3 Phase2): same but `<scope> = phase-<N>`

### Phase 4: Code Review (Code Review via Agent)

1. Delegate to Code Review via Agent → full review (Tier1), integration review (Tier2), minimal fix review (Tier3)
2. Critical/High/Medium → feedback loop: PM delegates corrections to Developer → Test re-validates → Code Review re-reviews → repeat until resolved or timeout (max 5 Tier1, 3 Tier2/3)
3. Low/Suggestions → incident_* entity if Memory MCP enabled, else listed in report for future
4. Verify: review report exists or approval; incidents persisted

### Phase 5: Documentation (Documentation via Agent) — STRICTLY BEFORE Phase 6, Tier-aware

1. Delegate to Documentation via Agent — tier-aware:
   - **Minimal (Small/Medium, Tier2, Tier3):** Glob `docs/specs/*` + `git diff --name-only HEAD` (via Bash or PM-provided diff) → if no specs exist or no diff skip (no write) else update ONLY changed specs incremental
   - **Full (Large):** specs incremental + docs/README.md + docs/PLANNING.md §Decisions if changed + docs/API_REFERENCE.md (if APIs)
2. **CHANGELOG.md is NOT created here** — DevOps exclusive (derived at close from git log + audit context)
3. Verify: Glob deliverables >0 or confirmed `no changes` → PM must verify before advancing to Phase 6
4. **Do NOT parallelize Phase 5 and 6** — DevOps must NOT start until Documentation reports completed and Glob verifies

### Phase 6: Git & Changelog (DevOps via Agent) — SEQUENTIAL AFTER Phase 5

1. After PM verifies Phase 5 Glob, delegate to DevOps via Agent:
   - `git add .` → `git commit -m "<conventional>"` (feat/fix/docs per tier) → `git branch -M` → `git push origin <branch>` (if remote exists)
   - Update `docs/CHANGELOG.md` derived at close from `git log --pretty` + audit/implementation context (see workflow.md §Document Ownership Map)
   - Full mode (Tier1 Large only): add CI/CD (`.github/workflows/ci.yml`) + deployment (Dockerfile, docker-compose.yml) + coverage threshold min 85%
2. Verify: `git log -1` exists + `git status` clean + Glob `docs/CHANGELOG.md` >0 (Full: + Glob `.github/workflows/*.yml`)

## File Integrity Checkpoints

| Delegation | Verify BEFORE | Verify AFTER |
|------------|---------------|--------------|
| PM: PRD+specs | — | `docs/PRD.md`, `docs/specs/*` content >0 |
| Test: TDD stubs | `docs/specs/<slug>.md` approved AC-N | `tests/<slug>.*` content >0, §10 mapping 100% AC→TC, tests FAIL |
| Architect: PLANNING | `docs/PRD.md`, `docs/specs/*` | `docs/PLANNING.md` + `docs/IMPLEMENTATION_ROADMAP.md` content >0 (M/L only) |
| Developer: implementation | `docs/specs/*`, `tests/*` (FAIL) + PLANNING if M/L + ROADMAP groups | `src/*` for group + `docs/PROJECT_CONTEXT.md` (tests now PASS, PM consolidated) |
| CodeReview: review | `src/*` exists | approval or incident_* (if MCP) in report |
| DevOps: commit | All above verified (Phase 5 Glob) | `git log -1` exists + `docs/CHANGELOG.md` derived |
| Documentation: specs sync | `docs/PROJECT_CONTEXT.md` + source | `docs/specs/*` synced if `git diff --name-only` shows change, else `no changes` |

Recovery: delegate to responsible agent → re-verify → escalate after 2 fails. Tier-aware pruning: Small/Tier0 skip PLANNING/ROADMAP gates.

## Agent Delegation Template (MANDATORY for every Agent call)

When delegating via Agent tool, compose prompt with (inline, pasted content — not just paths):

1. **Workflow Protocol Excerpt:** Relevant `.claude/rules/workflow.md` § for this phase:
   - Phase 1b/3/1b → `§TDD Protocol` + `§File Integrity Checkpoints` row
   - Phase 2 → `§File Integrity Checkpoints` + `§Memory MCP Protocol` decision_*
   - Phase 3/2/2 → `§Parallelization Protocol` + `§PROJECT_CONTEXT.md Race Prevention` + `§Rollback Protocol` + `§File Integrity` row
   - Phase 5/6 → `§Knowledge Transfer Protocol` + `§File Integrity`
2. **Required Skills — On Demand (for Developer/Architect):** Load ONLY relevant skill(s) for THIS task BEFORE implementing, 1-2 max matched to stack from PLANNING.md/project_*/specs. Example: Python → python-enterprise, TS/JS → typescript-enterprise, React → react-enterprise, Go → golang-engineer, Rust → rust-enterprise, Frontend → design-taste-frontend, Cloud → gcp-enterprise. If unknown → "Load on demand: pick single most relevant skill for this task, do NOT load others". For non-Developer agents: `No skill required`. Add step 1 in Task: "Load required skill(s) on demand and verify loaded before implementing"
3. **Spec/Context Attachments:** Relevant `docs/specs/*.md` paths+full content + PLANNING excerpt or project_*/ticket_* observations (via Read/Glob or Memory MCP) + `tests/<slug>.*` existence
4. **Task Scope:** Tier, phase, files to create/modify, AC, explicit `Verify BEFORE (Glob)` + `Verify AFTER (Glob+content>0)` gates from Prerequisite & Deliverable Table
5. **Output Contract:** What subagent must return (files created, verification Glob run, TodoWrite status) so PM can sync TodoWrite and run checkpoints. Agent system prompts are loaded automatically via `.claude/agents/<agent>.md` — do NOT paste them (redundant, wastes ~4.5k tokens per delegation).

Example Agent prompt skeleton:
```
Relevant workflow protocol for this phase:
<PASTE .claude/rules/workflow.md § excerpt>
---
Required skills — on demand (BEFORE starting):
<e.g., "Load on demand: `python-enterprise` only (stack: Python/FastAPI per docs/PLANNING.md). Do NOT load other skills. Verify loaded.">
---
Context:
- Tier: <0/1/2/3> Phase: <N> — <name>
- Specs: <path> (content pasted below)
- Planning: <PLANNING.md / specs/<feature>.md / project_*>
- Tests: <tests/<slug>.*> — exists: <yes/no> (Glob verified)
- Files in scope: <list>
---
Task: <concrete instruction> (include "Load required skills first" as step 1)
Verify BEFORE: <Globs>
Verify AFTER: <Globs + content checks>
Return: <files + verification output + todo status + skills loaded>

NOTE: Agent system prompt (.claude/agents/<agent>.md) is loaded automatically. Do NOT paste it — redundant.
```

## Parallelization (Claude Adaptation)

> Normative: `.claude/rules/workflow.md §Parallelization Protocol` for `Parallel group` markers and `PROJECT_CONTEXT.md Race Prevention`. PM launches same-group Developers together in SAME message (parallel Agent calls), waits all, consolidates PROJECT_CONTEXT.md once. Documentation (Phase 5) THEN DevOps (Phase 6) — STRICTLY SEQUENTIAL (DevOps must NOT start until Docs reports completed and Glob verifies). Sequential checkpointed phases must NOT be parallelized.

## Rollback Protocol (Hybrid — Backup Branch + Stashpoint — Claude Adaptation)

> Source: `.claude/rules/workflow.md §Rollback Protocol`. Before each Developer phase/group PM delegates DevOps to create TWO safety nets with unified `pre-<scope>` (`phase-<N>` or `group-<letter>`): `git branch backup/pre-<scope>-<timestamp>` + `git stash push -m "pre-<scope> - <name>" --keep-index --include-untracked` → verify both via `git branch --list "backup/pre-<scope>*"` + `git stash list` → if either fails retry once → escalate. After PASS clean both; after FAIL try `git stash pop --index` first, fallback `git reset --hard backup/...`, escalate if both fail, document `rollback(<scope>)` in CHANGELOG, post-rollback verify by running tests for complete scope. Same naming as OpenCode; Bash commands via Claude Bash tool.

## Adaptation Notes (OpenCode → Claude)

| OpenCode | Claude |
|----------|--------|
| `task` (`subagent_type`) | `Agent` (`subagent_type` same values: architect, developer, test, code-review, devops, documentation, Explore) |
| `read/glob/grep/bash/todowrite/question/context7_resolve-library-id` | `Read/Glob/Grep/Bash/TodoWrite/AskUserQuestion/WebSearch/WebFetch` (context7 → WebSearch/WebFetch) |
| `permission: {edit, write, bash: ask, task: allowlist}` | `tools: [...]` whitelist per agent + `.claude/settings.json` permissions |
| `~/.config/opencode/agents/*.md` | `.claude/agents/*.md` |
| `rules/workflow-protocols.md` SSOT | `.claude/rules/workflow.md` SSOT (adapted) |
| `memory` MCP `search_nodes/open_nodes/create_entities` | Optional `mcp__memory__*` if Memory MCP enabled in Claude Code; else inline context pasting via Read/Glob |
| Templates `~/.config/opencode/templates/context-files/` | `templates/context-files/` (`*-Claude.md` for PRD/SPEC/PROJECT_CONTEXT; others shared) |
