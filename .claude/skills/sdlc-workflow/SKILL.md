# SDLC Multi-Agent Workflow Skill

## When to Use
When the user says "build me...", "create a project", "add a feature",
"fix this bug", "start the workflow", "run the pipeline", or any
development task that benefits from structured SDLC.

## Workflow Overview

### Phase 0: Detect & Assess
1. Detect tier from user request (see CLAUDE.md Tier Detection)
2. If Tier 1: Ask complexity questions (modules, services, testing level)
3. Determine agent activation based on tier + size
4. Create feature branch: feature/<slug>, fix/<ticket>, direct/<desc>

### Phase 1: Requirements (Tier 1 only)
1. PM creates docs/PRD.md using template
2. PM creates docs/specs/<slug>.md with AC-N: GIVEN/WHEN/THEN
3. Verify: glob docs/PRD.md + docs/specs/*

### Phase 1b: TDD Stubs
1. For each spec: Test Agent creates tests/<slug>.*
2. 1 AC-N → 1 TC-00N mapping
3. Tests must initially FAIL
4. Verify: glob tests/<slug>.* + content exists

### Phase 2: Planning (Tier 1 Medium/Large only)
1. Architect creates docs/PLANNING.md
2. Architect creates docs/IMPLEMENTATION_ROADMAP.md
3. Mark Parallel groups (A, B, C...)
4. Verify: glob docs/PLANNING.md + docs/IMPLEMENTATION_ROADMAP.md

### Phase 3: Implementation
1. Group phases by Parallel group
2. For each group:
   a. Create safety nets (stash + backup branch)
   b. Delegate Developer per phase (parallel if same group)
   c. Test validates (max 3 iterations)
   d. On PASS: clean safety nets
   e. On FAIL: rollback (stash pop → backup → escalate)
3. Developer updates docs/PROJECT_CONTEXT.md after each phase

### Phase 4: Code Review
1. Code Review Agent reviews all implemented code
2. Critical/High/Medium → feedback loop (Developer fixes → Test re-validates)
3. Low/Suggestions → incident for future
4. Max 5 iterations (Tier 1) or 3 (Tier 2/3)

### Phase 5: Documentation
1. Docs sync specs (incremental: only if git diff shows change)
2. Tier 1 Large: also update README, API_REFERENCE, PLANNING

### Phase 6: Git & Changelog
1. DevOps commits with conventional commit message
2. DevOps generates CHANGELOG from git log
3. Push to feature branch

## File Integrity Checkpoints

| Delegation | Verify BEFORE | Verify AFTER |
|------------|---------------|--------------|
| PM: PRD+specs | — | docs/PRD.md, docs/specs/* |
| Test: TDD stubs | docs/specs/<slug>.md | tests/<slug>.* content >0 |
| Architect: PLANNING | docs/PRD.md, docs/specs/* | docs/PLANNING.md content >0 |
| Developer: implementation | docs/specs/*, tests/* | src/*, docs/PROJECT_CONTEXT.md |
| CodeReview: review | src/* | approval or incidents |
| DevOps: commit | All above verified | git log -1 exists |

## Agent Delegation Template

When delegating via Agent tool, compose prompt with:
1. Role description from the agent's .claude/agents/*.md
2. Task scope (tier, phase, files, criteria)
3. Spec/context content pasted inline
4. Required skill name (e.g., python-enterprise)
5. Verify BEFORE/after glob patterns
6. Output contract (what to return)
