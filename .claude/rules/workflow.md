# Workflow Protocols

## Document Ownership Map

| Document | Owner | Phase Created |
|----------|-------|---------------|
| docs/PRD.md | PM | Tier 1 Phase 1 |
| docs/specs/*.md | PM | Tier 1 Phase 1 |
| docs/PLANNING.md | Architect | Tier 1 Phase 2 (Medium/Large) |
| docs/IMPLEMENTATION_ROADMAP.md | Architect | Tier 1 Phase 2 (Medium/Large) |
| docs/PROJECT_CONTEXT.md | Developer | Each phase end |
| docs/CHANGELOG.md | DevOps | Final (derived from git log) |

## TDD Protocol

Sequence per phase:
1. PM creates spec: docs/specs/<slug>.md with AC-N: GIVEN/WHEN/THEN
2. Test creates stubs FIRST: 1 AC → 1 TC, tests must FAIL (red)
3. Developer implements ONLY to make tests PASS (green)
4. Test validates (max 3 iterations)
5. PM confirms phase completion

AC Format:
```
### AC-1: Description
- **GIVEN** precondition
- **WHEN** action
- **THEN** expected result
```

Rule: Developer NEVER starts without tests/<slug>.* existing.

## Parallelization

Roadmap phases have `Parallel group: <letter>`.
- Same group = parallel (launch together)
- Different groups = sequential (respect dependencies)

PROJECT_CONTEXT.md race condition:
- Developers in parallel do NOT write PROJECT_CONTEXT.md directly
- Each reports changes to PM in final report
- PM consolidates after entire group completes

## Rollback Protocol

Before each implementation phase:
1. git stash push -m "pre-<scope> - <name>" --keep-index --include-untracked
2. git branch backup/pre-<scope>-<timestamp>

Scope naming:
- Sequential execution: scope = phase-N (e.g., phase-3)
- Parallel group: scope = group-letter (e.g., group-A)

After success:
1. git stash drop stash@{0}
2. git branch -d backup/pre-<scope>-<timestamp>

After failure:
1. git reset --hard HEAD
2. git stash pop --index
3. If stash fails: git reset --hard backup/pre-<scope>-<timestamp>
4. If both fail: escalate to user

## File Integrity Checkpoints

| Delegation | Verify BEFORE | Verify AFTER |
|------------|---------------|--------------|
| PM: PRD+specs | — | docs/PRD.md, docs/specs/* |
| Test: TDD stubs | docs/specs/<slug>.md | tests/<slug>.* content >0 |
| Architect: PLANNING | docs/PRD.md, docs/specs/* | docs/PLANNING.md content >0 |
| Developer: implementation | docs/specs/*, tests/* | src/*, docs/PROJECT_CONTEXT.md |
| CodeReview: review | src/* | approval or incidents |
| DevOps: commit | All above verified | git log -1 exists |
