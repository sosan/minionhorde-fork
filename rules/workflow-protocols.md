# Shared Workflow Protocols

> **DOGMA: This file (`rules/workflow-protocols.md`) is the single source of truth.** Do not duplicate its content in `agents/` or `AGENTS.md`. All agents must reference this file via `rules/workflow-protocols.md §<Section>`.

These protocols are referenced by all agents. Do not duplicate them in individual agent files.

## Audit Log

Every workflow action is logged to `docs/AUDIT_LOG.md` for traceability. Simple append-only table — no hash chain.

### Entry Format

| Timestamp | Agent | Action | Target | Outcome | Details |
|-----------|-------|--------|--------|---------|---------|
| 2026-08-29 14:00 | PM | delegate | Architect | OK | Tier 1 Phase 2 |
| 2026-08-29 14:05 | Architect | create | docs/PLANNING.md | OK | 45 lines |
| 2026-08-29 14:15 | Developer | implement | src/auth/handler.go | OK | Phase 3 |
| 2026-08-29 14:30 | Test | execute | tests/auth_test.go | FAIL | 2/5 failed |

### Rules
- **Append-only** — never modify or delete existing entries
- Log every delegation, implementation, test run, review, commit, escalation, and rollback
- If `docs/AUDIT_LOG.md` doesn't exist when an agent needs to log, CREATE it with a `# Audit Log` header first
- Keep entries concise

---

## Document Ownership Map

Each document has a single responsible agent. This map is used by **File Integrity Checkpoints** to verify creation and trigger recovery if needed.

**Documents (formal, user-reviewed):**

| Document | Responsible Agent | Phase Created | Required By | Template |
|----------|------------------|---------------|-------------|----------|
| `docs/PRD.md` | Project Manager | Tier 1 Phase 1 | Architect, Test | `templates/context-files/PRD.md` |
| `docs/specs/*.md` | Project Manager | Tier 1 Phase 1 | Architect, Test, Developer (via PM delegation) | `templates/context-files/SPEC.md` |
| `docs/PLANNING.md` | Architect | Tier 1 Phase 2 (Medium/Large only; Small/Tier 0 skip — no gate) | Developer, Documentation | `templates/context-files/PLANNING.md` |
| `docs/IMPLEMENTATION_ROADMAP.md` | Architect (Developer for Tier 1 Small) | Tier 1 Phase 2 (Medium/Large only; Small skip — ROADMAP fused with workflow_* status) | Developer | `templates/context-files/IMPLEMENTATION_ROADMAP.md` |
| `docs/FEATURE_PLAN.md` | Architect | Tier 2 Phase 1 (Deprecated — create `docs/specs/<feature>.md` instead, same SPEC template) | Developer, Test | `templates/context-files/FEATURE_PLAN.md` |
| `docs/PROJECT_CONTEXT.md` | Developer | Each phase end | Documentation, PM | `templates/context-files/PROJECT_CONTEXT.md` |
| `docs/CHANGELOG.md` | DevOps | Final phases (Derived — generated at close from `git log` + `audit_*`/`implementation_*`, not per-phase gate) | PM, Documentation | `templates/context-files/CHANGELOG.md` |
| `docs/README.md` | Documentation | Tier 1 Large Phase 6 (Large only) | Project index | `templates/context-files/README.md` |
| `docs/API_REFERENCE.md` | Documentation | Tier 1 Large Phase 6 (Large only, if APIs) | Developer, API consumers | `templates/context-files/API_REFERENCE.md` |

**Memory entities (persistent, queryable):**

| Entity Type | Owner | Replaces | Phase Created | Required By |
|-------------|-------|----------|---------------|-------------|
| `project_*` | PM | `docs/EXISTING_CONTEXT.md` (Tier 2) | Tier 2 Phase 0 (only if Tier 1 specs exist; else skip, use `glob` direct) | Architect |
| `ticket_*` | PM | `docs/TICKET_ANALYSIS.md` (Tier 3) | Tier 3 Phase 0 | Developer |
| `decision_*` | Architect | — (complements PLANNING.md) | Tier 1 Phase 2 (only if PLANNING.md created — Medium/Large) | Developer, Documentation |
| `implementation_*` | Developer | — (view of PROJECT_CONTEXT.md — add_observations test_status/coverage/commit only) | Each phase end | Test, Code Review, DevOps |
| `root_cause_*` | Developer | `docs/ROOT_CAUSE.md` (Tier 3) | Tier 3 Phase 1 | Developer (Phase 2), Test |
| `incident_*` | Code Review | `docs/REPORT.md` | Post-review | Future reference |
| `audit_*` | Any agent | `docs/AUDIT_LOG.md` (source; AUDIT_LOG.md generated on-demand at close) | Ongoing | PM, Compliance |

**Note:** `docs/specs/*.md` are kept in sync by the Documentation Agent (minimal scope) in ANY tier where implementation changed the functionality and spec files exist. Use `git diff --name-only HEAD` to check if specs actually changed — skip write if no diff.

**Tier-aware pruning:** See `§Document Ownership Map` notes above. Do not create or gate artefacts for tiers that skip them (Tier 0: 0 docs; Tier 1 Small: PRD+specs+PROJECT_CONTEXT only; Tier 1 Large: +PLANNING/ROADMAP/README/API_REFERENCE). `workflow_*` is metric-only (start/end/duration), not a gate; `AUDIT_LOG.md` is generated on-demand from `audit_*` at close, not continuously.

---

## Feature Branch Policy

Every workflow creates and works on an isolated feature branch. No implementation happens on the default branch.

### Branch Naming Convention

| Tier | Format | Example |
|------|--------|---------|
| Tier 0 (direct) | `direct/<short-desc>` | `direct/fix-typos` |
| Tier 1 (new project) | `feature/<project-slug>` | `feature/task-api` |
| Tier 2 (feature addition) | `feature/<feature-slug>` | `feature/oauth2-login` |
| Tier 3 (bug fix) | `fix/<ticket-number>-<short-desc>` | `fix/142-token-refresh` |

### When to Create

| Tier | Creation Point | Base Branch |
|------|---------------|-------------|
| Tier 0 | Phase 0 (after user confirms direct mode) | default branch |
| Tier 1 | Phase 0 (after complexity assessment) | default branch |
| Tier 2 | Phase 0 (after codebase analysis) | default branch |
| Tier 3 | Phase 0 (after ticket analysis) | default branch |

### Branch Lifecycle

```
Create → Work (all phases) → Merge → Delete
```

1. **Create** — DevOps creates the feature branch at workflow start (Phase 0)
2. **Work** — All implementation, testing, and review happens on this branch
3. **Merge** — After human sign-off, DevOps merges to default branch (PR flow unchanged)
4. **Delete** — After successful merge, DevOps deletes the feature branch

### Integration with Rollback Protocol

The rollback protocol (`§Rollback Protocol`) safety nets (`backup/pre-<scope>-<timestamp>` and stashpoints) work **IN ADDITION** to the feature branch:

- **Feature branch** = the working branch for the entire workflow
- **Backup branches** = point-in-time snapshots BEFORE each phase/group (on the feature branch)
- **Stashpoints** = fast restore mechanism (on the feature branch)

```
feature/oauth2-login  (main working branch, exists entire workflow)
  ├── backup/pre-phase-1-20260831T120000  (snapshot before phase 1)
  ├── backup/pre-group-A-20260831T120000 (snapshot before parallel group A)
  └── stash: pre-phase-2 - auth-module   (fast restore point)
```

The feature branch is **NEVER** reset or deleted during rollback. Only backup branches and stashpoints are managed by the rollback protocol.

### Merge Policy

- **Tier 0:** Merge `direct/<short-desc>` → default
- **Tier 1:** Merge `feature/<project-slug>` → default
- **Tier 2:** Merge `feature/<feature-slug>` → default
- **Tier 3:** Merge `fix/<ticket-number>-<short-desc>` → default
- **Human sign-off required before merge** (existing policy, unchanged)
- **Merge method:** per DevOps preferences (merge/rebase/squash)

---

## TDD Protocol — Spec → Test → Code (MANDATORY)

Every feature phase follows strict TDD with spec as single source of truth. Violating order blocks downstream phases.

### Sequence (per roadmap phase / feature)

1. **PM creates spec** — `docs/specs/<feature-slug>.md` with Acceptance Criteria in format `### AC-N: GIVEN / WHEN / THEN`. Spec status `approved` gates next step.
2. **PM delegates Test (FIRST)** — Test Agent reads spec ACs and creates `tests/<slug>.*` stubs: `1 AC-N → 1 TC-00N`. Tests must initially FAIL (red). Verify with `glob` that test file exists; coverage = `TCs / ACs` must be 100% before Developer starts.
3. **PM delegates Developer (SECOND)** — Developer reads spec + tests and implements ONLY to make tests pass. No source before tests — if `glob` for test file fails, Developer reports to PM and does NOT proceed.
4. **Test validates** — Test executes tests + regression suite. PASS → phase completes. FAIL → feedback loop (max 3 iterations per AGENTS.md §Test Feedback Loop).
5. **PM confirms phase** — Only after Test reports `PASS + 100% AC→TC coverage` does PM advance to next phase.

### AC Format

Each Acceptance Criteria uses three keywords:

```markdown
### AC-1: User login
**GIVEN** valid user credentials
**WHEN** user submits login
**THEN** returns JWT token

### AC-2: Invalid credentials
**GIVEN** wrong password
**WHEN** user submits login
**THEN** returns 401 error
```

- One AC per behavior path. Use separate ACs for alternative paths.
- GIVEN = preconditions, WHEN = actions, THEN = expected outcome

### Violations

- If Developer is delegated without pre-existing tests → Developer reports missing test to PM, does NOT implement
- If Test creates tests not mapped to an AC → reject; PM must first add AC to spec
- If spec AC is modified after approval → Test regenerates tests, Developer re-implements

---

## File Integrity Checkpoints — Phase-Gate Verification

**Problem:** A downstream agent may be delegated a task that requires a document which was never created. This causes silent failures or incorrect behavior.

**Solution:** Before delegating any agent, verify (glob) that all prerequisite documents exist. After delegation, verify the deliverable exists with content > 0 lines. If missing → delegate recovery to the responsible agent → re-verify → escalate to human after 2 failed attempts.

### Prerequisite & Deliverable Table

| Delegation | Verify BEFORE (prerequisites) | Verify AFTER (deliverable) | Recovery via |
|---|---|---|---|
| Tier 1 Ph 1 — PM: PRD + specs | — | `docs/PRD.md`, `docs/specs/*` (each spec has Acceptance Criteria section with AC-N) | PM creates directly |
| Tier 1 Ph 1b — Test: TDD stubs (per spec) | `docs/specs/<slug>.md` (approved, passes AC format gate) | `tests/<slug>.*` + `docs/specs/<slug>.md §10 Test Scenarios Mapping` (100% AC→TC). Tests must initially FAIL (red phase) | Test |
| Tier 1 Ph 2 — Architect (Developer for Small): PLANNING + ROADMAP | `docs/PRD.md`, `docs/specs/*` | `docs/PLANNING.md` (Medium/Large only) + `docs/IMPLEMENTATION_ROADMAP.md` with `status` per phase | Architect (Medium/Large only; Small skip — no gate) |
| Tier 1 Ph 3 — Test: TDD stubs (per phase, if not done in 1b) | Relevant `docs/specs/<slug>.md` (approved) | `tests/<slug>.*` + `§10` mapping (100% AC→TC). Tests must initially FAIL | Test |
| Tier 1 Ph 3 — Developer: implementation (TDD) — grouped by `Parallel group` | `docs/specs/<slug>.md` (approved) + `tests/<slug>.*` (exists, initially FAIL) + `docs/PLANNING.md` (if Medium/Large) + `docs/IMPLEMENTATION_ROADMAP.md` with `Parallel group` + `status` | Source files for group + consolidated `docs/PROJECT_CONTEXT.md` (tests now PASS) — PM consolidates after group | Developer(s) in parallel per group |
| Tier 2 Ph 0 — PM: project context | — | `project_*` entity (only if Tier 1 specs exist; else skip) | PM creates directly |
| Tier 2 Ph 1 — Architect: specs for feature | `project_*` entity exists (if applicable) | `docs/specs/<feature>.md` (Deprecated: `FEATURE_PLAN.md` → use `specs/<feature>.md` SPEC template) | Architect |
| Tier 2 Ph 1b — Test: TDD stubs (feature) | `docs/specs/<feature>.md` (approved) § Tests | `tests/<slug>.*` + `§10` mapping (100% AC→TC). Tests must initially FAIL | Test |
| Tier 2 Ph 2 — Developer: implementation (TDD) | `docs/specs/<feature>.md` (approved) + `project_*` (if applicable) + `tests/<slug>.*` (exists) + relevant `docs/specs/<slug>.md §9` | Source files + `docs/PROJECT_CONTEXT.md` (tests PASS) | Developer |
| Tier 1 Ph 5 — Documentation: final docs | `docs/PROJECT_CONTEXT.md` + source files | `docs/specs/*` synced (if `glob` + `git diff --name-only` shows change) — Medium/Large: + `docs/PLANNING.md` §Decisions if changed; Large only: + `docs/README.md` + `docs/API_REFERENCE.md` (if APIs) — each with content >0 | Documentation |
| Tier 1 Ph 6 — DevOps: commit | Phase 5 verified (`glob` PASS; Small: specs sync verified or skipped) | `docs/CHANGELOG.md` derived (generated at close from `git log` + `audit_*`) + commit `git log -1` exists + `git status` clean | DevOps |
| Tier 2 Ph 5 — Documentation: specs sync | `docs/specs/*` exists + `docs/specs/<feature>.md` | `docs/specs/*` synced if `git diff --name-only` shows change | Documentation |
| Tier 2 Ph 6 — DevOps: commit | Phase 5 verified or skipped | commit + CHANGELOG derived | DevOps |
| Tier 3 Ph 5 — Documentation: specs sync | `docs/specs/*` exists (if Tier 1 existed) | `docs/specs/*` synced if fix changed functionality | Documentation |
| Tier 3 Ph 6 — DevOps: commit | Phase 5 verified (`glob` PASS) | commit `fix(... ) #<ticket>` + CHANGELOG | DevOps |
| Tier 3 Ph 0 — PM: ticket analysis | — | `ticket_*` entity in memory (search_nodes("ticket_<number>")) | PM creates directly |
| Tier 3 Ph 1 — Developer: root cause | `ticket_*` entity exists | `root_cause_*` entity in memory (search_nodes("root_cause_<ticket>")) | Developer |
| Tier 3 Ph 2 — Developer: bug-repro test + fix | `root_cause_*` entity exists | Bug-reproduction `tests/<slug>.*` (initially FAIL) → fix source → test PASS + `docs/PROJECT_CONTEXT.md` | Developer |

### Recovery Protocol

1. **Identify** the responsible agent from the Document Ownership Map
2. **Delegate** a recovery task with explicit context: document needed, why (downstream phase), any partial content, source docs to reference
3. **Re-verify** the file exists and has content > 0 lines
4. **Escalate** to human if: recovery fails after 2 attempts, the agent reports it cannot create the document, or the missing document blocks a critical phase

## Parallelization Protocol

> **PM MUST read this section before Tier 1 Phase 3 and before every finalization (Phases 5/6).** Do NOT delegate Developers or Documentation/DevOps without applying `PM Execution Rules` and `PROJECT_CONTEXT.md Race Condition Prevention` below. Optimize `glob` usage: batch independent `glob` checks for `tests/<slug>.*` in parallel, prefer specific patterns over `**/*`.

When multiple modules or phases can be executed concurrently, use explicit parallelization markers to coordinate execution.

### Parallel Group Markers in IMPLEMENTATION_ROADMAP.md

The Architect (or Developer for Tier 1 Small) marks phases with parallel group identifiers:

```markdown
### Phase 3a: Authentication Module (parallelizable)
- Files: src/auth/handler.go, src/auth/middleware.go
- Tests: tests/auth_test.go
- Dependencies: none
- Parallel group: A

### Phase 3b: API Endpoints (parallelizable)
- Files: src/api/routes.go, src/api/handlers.go
- Tests: tests/api_test.go
- Dependencies: none
- Parallel group: A

### Phase 3c: Database Layer (sequential)
- Files: src/db/repository.go, src/db/models.go
- Tests: tests/db_test.go
- Dependencies: 3a, 3b (needs auth + API interfaces)
- Parallel group: B

### Phase 4: Integration (sequential)
- Files: src/main.go
- Tests: tests/integration_test.go
- Dependencies: 3a, 3b, 3c
- Parallel group: C
```

### Marking Rules

When creating `IMPLEMENTATION_ROADMAP.md`:
1. Analyze module dependencies
2. Group independent modules into parallel groups (A, B, C...)
3. Mark each phase with: `Parallel group: <letter>`
4. Phases in the **same** parallel group can run in parallel
5. Phases in **different** groups must run sequentially (respect dependencies)

### PM Execution Rules

When delegating implementation phases:
1. Read roadmap parallel group markers
2. If multiple phases share the same parallel group → launch ALL in a **single message** (parallel task calls)
3. Wait for ALL to complete before proceeding to next group
4. Never parallelize phases from different groups
5. PROJECT_CONTEXT.md updates: each Developer reports changes to PM; PM consolidates after the entire parallel group completes (avoids race condition on PROJECT_CONTEXT.md)

### PROJECT_CONTEXT.md Race Condition Prevention

When multiple Developers run in parallel within the same group:
- Each Developer reports their PROJECT_CONTEXT.md changes to the PM in their final report
- Developers **do not** write to PROJECT_CONTEXT.md directly during parallel execution
- After all Developers in the group complete, the PM consolidates changes into PROJECT_CONTEXT.md
- Once the group is done and PROJECT_CONTEXT.md is updated, the next sequential group can begin

---

## Rollback Protocol (Hybrid — Backup Branch + Stashpoint)

> **Dogma: This is the single source of truth for rollback.** `AGENTS.md` and `agents/project-manager.md` must not redefine names or steps — they reference this section. The hybrid model preserves BOTH safety nets: stash (fast, `pop --index`) + branch (hard, `reset --hard backup/...`).

### Naming Convention (Unified — eliminates divergence)

All safety nets use the unified scope placeholder `<scope>`:

- **Sequential execution (Tier 2 Phase 2, Tier 3 Phase 2, or Tier 1 without parallel groups):** `<scope> = phase-<N>` (e.g., `phase-3`, `phase-2`)
- **Parallel-group execution (Tier 1 Phase 3 with `Parallel group: <letter>`):** `<scope> = group-<letter>` (e.g., `group-A`, `group-B`)

This single convention replaces the previous divergence `pre-phase-<N>` vs `pre-group-<letter>` — now both are `pre-<scope>`.

- **Backup branch:** `backup/pre-<scope>-<timestamp>` (e.g., `backup/pre-phase-3-20260831T120000`, `backup/pre-group-A-20260831T120000`)
- **Stashpoint message:** `pre-<scope> - <name>` (e.g., `pre-phase-3 - auth-module`, `pre-group-A - auth+api`)

### Pre-phase Safety Net Creation (BEFORE Developer phase/group)

Before each Developer phase (Tier 1 Phase 3 / Tier 2 Phase 2 / Tier 3 Phase 2):

1. **PM delegates to DevOps** to create TWO safety nets with the unified `<scope>`:
   - **Backup branch:** `git branch backup/pre-<scope>-<timestamp>` (permanent safety net)
   - **Stashpoint:** `git stash push -m "pre-<scope> - <name>" --keep-index --include-untracked` (fast restore)
2. **Verify both exist:**
   - `git branch --list "backup/pre-<scope>*"` — backup branch must exist
   - `git stash list` — stash entry must exist (message contains `pre-<scope>`)
3. If either fails → retry once (see AGENTS.md §Retry Protocol); if still fails → escalate to human immediately — do NOT proceed without safety nets

### Post-phase Success (PASS)

After Test Agent validates successfully for the `<scope>`:

1. **Clean stashpoint:** `git stash drop stash@{0}`
2. **Clean backup branch:** `git branch -d backup/pre-<scope>-<timestamp>`
3. Verify both cleaned: `git stash list` (no matching `pre-<scope>`) + `git branch --list "backup/pre-<scope>*"` (no match)

### Post-phase Failure (ROLLBACK)

If validation fails after max iterations and the `<scope>` cannot be resolved:

1. **Stop** — Do not proceed to the next phase/group
2. **Attempt fast restore (stashpoint first):**
   - `git reset --hard HEAD` — clean working dir of failed scope
   - `git stash pop --index` — restore stashed state for `pre-<scope>`
   - Verify with `git status` and `git stash list`
3. **If stash fails → fallback to backup branch:**
   - `git reset --hard backup/pre-<scope>-<timestamp>` — restore to pre-scope state
   - Verify with `git status` and `git log -1`
4. **If backup branch fails → escalate to human immediately** — do NOT attempt manual conflict resolution
5. **Document** the rollback in `docs/CHANGELOG.md` with reason, backup branch name (`backup/pre-<scope>-<timestamp>`), and reverted commits
6. **Escalate** — Present to human for decision: adjust requirements, accept partial implementation, or redesign

### Rules

- **Preferred restore:** `stash pop --index` (fast, non-destructive) — always try first
- **Backup branch is safety net:** only used if stash restore fails — never the first option
- **Never:** `git stash clear` or `git reset --hard` on main without PM approval
- **Never proceed without safety nets:** if both backup branch and stashpoint creation fail, escalate immediately
- **Consolidated naming:** Always use `pre-<scope>` (`phase-<N>` or `group-<letter>`); never invent `pre-phase` vs `pre-group` as separate conventions

---

## Knowledge Transfer Protocol

After workflow completion, ensure the project state is properly captured for future workflows.

### When to Activate
- After Phase 6 (Tier 1 Large) or after the final phase in any tier
- Before starting a NEW workflow on the same project (Tier 2 or Tier 3)

### Protocol

1. **Verify PROJECT_CONTEXT.md is current** — The Developer updates it after each phase, but the PM must verify it reflects the final state:
   - Delegate to Developer: review and update `docs/PROJECT_CONTEXT.md` with final implementation state
   - Verify: `glob "docs/PROJECT_CONTEXT.md"` exists and has content > 20 lines

2. **Verify specs are in sync** — If `docs/specs/` exists, delegate to Documentation Agent to verify specs match implementation

3. **Capture workflow learnings** — After Tier 1 Large or complex Tier 2, create `incident_*` entities in memory:
   - Use `create_entities` to create `incident_workflow_<type>_<timestamp>` entities
   - Include: what worked well, what caused delays, agent coordination friction points
   - This helps optimize future workflows on the same project

4. **Handoff summary** — When starting a new workflow on an existing project:
   - Use `search_nodes("project_<name>")` to load project context from memory
   - Use `search_nodes("incident_workflow")` to find workflow learnings
   - Read `docs/PROJECT_CONTEXT.md` for current state
   - Read `docs/specs/*.md` for functional specifications
   - These inform the new workflow's planning phase

### Output
No separate document is created. The knowledge lives in PROJECT_CONTEXT.md (state), incident_* entities in memory (learnings), and specs/ (specifications) — all already owned by their respective agents.

---

## Memory MCP Protocol

The Memory MCP provides persistent knowledge graph storage across sessions. This section is the **single source of truth** for memory usage. Do not duplicate these instructions in individual agent files.

### Available Tools

| Tool | Purpose | Token Cost |
|------|---------|------------|
| `create_entities` | Create new entities in the graph | Low |
| `create_relations` | Create directed relations between entities | Low |
| `add_observations` | Add atomic facts to existing entities | Low |
| `open_nodes` | Retrieve specific entities by name | Low |
| `search_nodes` | Search entities by substring match | Low |
| `read_graph` | **Read entire knowledge graph** | **HIGH — avoid** |
| `delete_entities` | Remove entities | Low |
| `delete_observations` | Remove specific observations | Low |
| `delete_relations` | Remove relations | Low |

### Token Efficiency Rules

1. **NEVER use `read_graph`** — loads entire graph, wastes tokens
2. **Prefer `open_nodes`** when you know the entity name
3. **Prefer `search_nodes`** when searching by topic
4. **Keep observations atomic** — one fact per string, max 100 characters
5. **Limit entity count** — minimal active entities per workflow

### Entity Types

| Type | Owner | Purpose | Naming Convention |
|------|-------|---------|-------------------|
| `project_*` | PM | Current project state | `project_<name>` |
| `workflow_*` | PM | Workflow progress | `workflow_<tier>_<feature>_<YYYYMMDD>` |
| `ticket_*` | PM | Ticket analysis (Tier 3) | `ticket_<number>_<YYYYMMDD>` |
| `decision_*` | Architect | Technical decisions | `decision_<topic>_<YYYYMMDD>` |
| `implementation_*` | Developer | Code implementation state | `implementation_<feature>_<phase>_<YYYYMMDD>` |
| `root_cause_*` | Developer | Bug root cause analysis (Tier 3) | `root_cause_<ticket>_<YYYYMMDD>` |
| `incident_*` | Code Review | Low/Suggestions incidents | `incident_<type>_<YYYYMMDD>T<HHMMSS>` |
| `audit_*` | Any agent | Event logging | `audit_<YYYYMMDD>T<HHMMSS>` |

### Entity Ownership Rules

| Entity Type | Can Create | Can Add Observations | Can Delete |
|-------------|------------|---------------------|------------|
| `project_*` | PM | PM | PM |
| `workflow_*` | PM | PM | PM |
| `ticket_*` | PM | PM | PM |
| `audit_*` | Any agent | Any agent | PM (cleanup) |
| `decision_*` | Architect | Architect | Architect |
| `implementation_*` | Developer | Developer, Test, Code Review, DevOps | Developer |
| `root_cause_*` | Developer | Developer | Developer |
| `incident_*` | Code Review | Code Review | PM (cleanup) |

### Project State Entity (`project_*`)

Created by PM at workflow start. Stores current project context for cross-session persistence.

**Example:**
```json
{
  "name": "project_swarn",
  "entityType": "project",
  "observations": [
    "name: swarn",
    "tech_stack: Python, FastAPI, SQLAlchemy",
    "architecture: Clean Architecture",
    "test_framework: pytest",
    "current_module: auth",
    "last_phase_completed: 2_implementation",
    "coding_style: type_hints_required"
  ]
}
```

### Workflow State Entity (`workflow_*`)

Created by PM at Phase 0. Tracks workflow progress with timing.

**Example:**
```json
{
  "name": "workflow_tier2_auth_20260829",
  "entityType": "workflow_state",
  "observations": [
    "tier: 2",
    "feature: authentication",
    "current_phase: 2_implementation",
    "iteration_count: 1",
    "max_iterations: 3",
    "current_agent: developer",
    "session_id: ses_abc123",
    "start_time: 2026-08-29T10:00:00Z",
    "end_time: 2026-08-29T12:30:00Z",
    "duration: 9000",
    "phase_0_duration: 600",
    "phase_1_duration: 1800",
    "phase_2_duration: 3600",
    "phase_3_duration: 1200",
    "phase_4_duration: 900",
    "phase_5_duration: 600"
  ]
}
```

**Timing Fields:**
- `start_time`: ISO 8601 timestamp when workflow started
- `end_time`: ISO 8601 timestamp when workflow completed (empty if in progress)
- `duration`: Total elapsed time in seconds
- `phase_N_duration`: Duration of each phase in seconds (updated as phases complete)

**PM Responsibilities for Workflow Timing:**
- Record `start_time` at workflow start (Phase 0)
- Update `current_phase` and `phase_N_duration` when each phase completes
- Record `end_time` and `duration` when workflow completes
- Calculate total duration from sum of phase durations

### Ticket Analysis Entity (`ticket_*`)

Created by PM at Tier 3 Phase 0. Replaces `docs/TICKET_ANALYSIS.md`.

**Example:**
```json
{
  "name": "ticket_142_20260829",
  "entityType": "ticket_analysis",
  "observations": [
    "ticket_number: 142",
    "summary: Token refresh fails silently",
    "affected_component: auth/token_service",
    "reproduction_steps: 1. Login, 2. Wait for token expiry, 3. Call refresh endpoint",
    "expected: New token returned",
    "actual: 401 error, no token returned",
    "priority: high",
    "initial_hypothesis: Race condition in token rotation"
  ]
}
```

### Decision Entity (`decision_*`)

Created by Architect. Stores technical decisions with rationale.

**Example:**
```json
{
  "name": "decision_auth_jwt_20260829",
  "entityType": "technical_decision",
  "observations": [
    "author: architect",
    "category: authentication_pattern",
    "decision: JWT with refresh tokens",
    "rationale: Stateless auth suitable for microservices",
    "alternatives_rejected: session-based (stateful), OAuth2 (over-engineered)",
    "files_affected: src/auth/handler.go, src/auth/middleware.go",
    "project: project_swarn"
  ],
  "relations": [
    {"from": "decision_auth_jwt_20260829", "to": "project_swarn", "relationType": "decision_for"}
  ]
}
```

### Implementation Entity (`implementation_*`)

Created by Developer. Multiple agents may add observations.

**Example:**
```json
{
  "name": "implementation_auth_phase2_20260829",
  "entityType": "implementation_state",
  "observations": [
    "author: developer",
    "phase: 2",
    "files_modified: src/auth/handler.go, src/auth/middleware.go",
    "test_status: 5/5 passing",
    "coverage: 87%",
    "review_status: PASS",
    "commit_hash: abc1234"
  ],
  "relations": [
    {"from": "implementation_auth_phase2_20260829", "to": "project_swarn", "relationType": "part_of"},
    {"from": "implementation_auth_phase2_20260829", "to": "decision_auth_jwt_20260829", "relationType": "implements"}
  ]
}
```

### Root Cause Entity (`root_cause_*`)

Created by Developer at Tier 3 Phase 1. Replaces `docs/ROOT_CAUSE.md`.

**Example:**
```json
{
  "name": "root_cause_142_20260829",
  "entityType": "root_cause_analysis",
  "observations": [
    "ticket: ticket_142_20260829",
    "root_file: src/auth/token_service.py",
    "root_line: 142",
    "technical_explanation: Race condition when two requests refresh simultaneously — second request uses expired token from cache",
    "proposed_fix: Add mutex lock around token rotation",
    "test_needed: Concurrent refresh test with 10 parallel requests"
  ],
  "relations": [
    {"from": "root_cause_142_20260829", "to": "ticket_142_20260829", "relationType": "analyzes"}
  ]
}
```

### Incident Entity (`incident_*`)

Created by Code Review. Replaces `docs/REPORT.md`.

**Example:**
```json
{
  "name": "incident_low_style_20260829T143000",
  "entityType": "incident",
  "observations": [
    "severity: low",
    "category: code_style",
    "file: src/auth/handler.py",
    "line: 45",
    "description: Inconsistent naming convention — function uses camelCase instead of snake_case",
    "suggestion: Rename to get_user_by_id",
    "status: for_future_consideration",
    "project: project_swarn"
  ]
}
```

### Audit Event Entity (`audit_*`)

Created by any agent. Logs workflow events with timing.

**Example:**
```json
{
  "name": "audit_20260829T143000",
  "entityType": "audit_event",
  "observations": [
    "timestamp: 2026-08-29T14:30:00Z",
    "start_time: 2026-08-29T14:30:00Z",
    "end_time: 2026-08-29T14:45:00Z",
    "duration: 900",
    "from: project-manager",
    "to: developer",
    "action: delegate_implementation",
    "target_files: src/auth/*.go",
    "status: completed",
    "phase: 3",
    "tier: 1"
  ]
}
```

**Timing Fields:**
- `start_time`: ISO 8601 timestamp when the action started
- `end_time`: ISO 8601 timestamp when the action completed (empty if in progress)
- `duration`: Elapsed time in seconds (calculated: end_time - start_time)

**Agent Responsibilities for Timing:**
- **PM**: Records timing for delegations, phase transitions, escalations
- **Developer**: Records timing for implementation phases, code changes
- **Test**: Records timing for test execution, validation
- **Code Review**: Records timing for reviews, feedback loops
- **DevOps**: Records timing for git operations, deployments
- **Documentation**: Records timing for doc updates, report generation

### Agent Quick Reference

| Agent | Create | Add Observations | Read | Timing Responsibilities |
|-------|--------|-----------------|------|-------------------------|
| **PM** | `project_*`, `workflow_*`, `ticket_*`, `audit_*` | All owned entities | All | Record workflow start/end, phase transitions, delegations |
| **Architect** | `decision_*` | Own `decision_*` | All | Record planning/research duration |
| **Developer** | `implementation_*`, `root_cause_*` | Own `implementation_*`, `root_cause_*` | All | Record implementation phases, code changes |
| **Test** | — | `implementation_*` (test results) | All | Record test execution, validation duration |
| **Code Review** | `incident_*` | Own `incident_*`, `implementation_*` (review status) | All | Record review duration, feedback loops |
| **DevOps** | — | `implementation_*` (commit/branch) | All | Record git operations, deployment duration |
| **Documentation** | — | — (read-only) | All (for report generation) | Record doc updates, report generation duration |

### Integration with Existing Protocols

Memory entities **complement, not replace** formal markdown documents:

| Formal Document (kept as markdown) | Memory Entity (replaces informal doc) |
|-------------------------------------|---------------------------------------|
| `docs/PRD.md` | — (formal, user-reviewed) |
| `docs/specs/*.md` | — (formal, user-reviewed) |
| `docs/PLANNING.md` | `decision_*` (complements with rationale) |
| `docs/IMPLEMENTATION_ROADMAP.md` | `workflow_*` (persists phase progress) |
| `docs/PROJECT_CONTEXT.md` | `implementation_*` (complements with structured state) |
| `docs/CHANGELOG.md` | — (formal version history) |
| `docs/README.md` | — (human-facing) |
| `docs/API_REFERENCE.md` | — (human-facing) |
| `docs/AUDIT_LOG.md` | `audit_*` (replaces append-only log) |
| `docs/EXISTING_CONTEXT.md` | `project_*` (replaces Tier 2 context snapshot) |
| `docs/TICKET_ANALYSIS.md` | `ticket_*` (replaces Tier 3 ticket breakdown) |
| `docs/ROOT_CAUSE.md` | `root_cause_*` (replaces Tier 3 root cause analysis) |
| `docs/REPORT.md` | `incident_*` (replaces Low/Suggestions incidents) |

### Conflict Prevention

- Each entity type has a single creator — only that agent creates new entities
- Authorized agents may add observations to existing entities
- Use `add_observations` (not `create_entities`) to update existing state
- PM is the only agent that may delete entities (cleanup after workflow completion)
