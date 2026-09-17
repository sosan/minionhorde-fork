# Bootstrap Curriculum

Sequence for procedural calibration. Roles of judgment get the full cycle; execution roles get automation plus checks.

## General sequence

```
Orientation
  -> Canonical patterns
  -> Adversarial cases
  -> Structured reflection
  -> Mutated cases (transfer)
  -> Tone exam
  -> Real work with external checks
  -> Incidents -> patterns -> refinement
```

## Layer 0 — Orientation (brief)

- Agent objective.
- Security limits (reference to CORE + policy, without duplicating).
- Instruction hierarchy.
- Available tools.
- What is verified externally (checks) instead of by discipline.

## Layer 1 — Canonical patterns

One worked case per pattern: risk classification, preflight, TDD, parallelization, recovery, security refusal.

## Layer 2 — Adversarial cases

Two rules compete: speed vs security, scope vs fix, rollback vs others' changes, documentation vs minimum.

## Layer 3 — Structured reflection

Output format (verifiable artifact):
- Relevant constraints
- Options considered
- Main risk
- Decision
- Required check
- Escalation condition

## Layer 4 — Mutation

Change the details: another file, another phase, another agent, another risk, another failure cause. Measures transfer, not memory.

## Exam

Uses `exam/tone-audit.md`.

## Variants by role

- **Decision** (PM, Architect, Code Review): full cycle + cross-model crystallization + role memory.
- **Execution** (Developer, Test, DevOps, Documentation): automated rules + external checks + incident memory.

## Variants by tier

- Tier 0: brief orientation + 1 canonical case + minimal exam.
- Tier 1-2: full cycle according to role.
- Tier 3: orientation + recovery case + tone exam of the affected area.