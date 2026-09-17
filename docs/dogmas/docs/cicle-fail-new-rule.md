# FAIL Cycle → New Rule ID

## Purpose

When an evaluation case results in FAIL, the system must generate a new rule ID that captures the failure pattern and integrates it into the CORE. This mechanism implements the learning cycle (AC-16).

## Mechanism

### 1. Detect FAIL

The scoring rubric (`eval/tone-audit.md`) classifies each response as PASS, PARTIAL, or FAIL. FAIL means the agent performed a prohibited action or violated an invariant.

### 2. Record the incident

Record the FAIL in `MEMORY/README.md` using:

```markdown
### incident_<date>_<case>
- **Situation:** case and context
- **Decision:** what the agent did (the violation)
- **Reason:** why the agent made that decision (bias, omission, interpretation error)
- **Transfer:** which decision pattern failed and how to avoid it in the future
```

### 3. Analyze the pattern

After recording the incident, ask:

- **Is it repeatable?** The same failure in ≥2 independent cases is a pattern.
- **Which CORE invariant is involved?** Identify the invariant that should have prevented it.
- **Is the invariant insufficient?** An existing invariant may need expansion; an absent one may need creation.

### 4. Generate the new rule ID

If analysis requires a new rule:

1. Assign a unique ID using the convention:
   - `A-XX` new axioms
   - `PR-XX` precedence
   - `TM-XX` threats
   - `I-XX` injection
   - `R-XX` secrets
   - `X-XX` exfiltration
   - `D-XX` destructive actions
   - `W-XX` weakening
   - `S-XX` supply chain
   - `B-XX` scope
   - `T-XX` testing
   - `APR-XX` approval
   - `IR-XX` incident response
   - `B.XX` machine guards
   - `DC-XX` default rule
   - `DE-XX` evaluation suite
2. Document it in `new-rule-ids.md` with **Rule**, **Reason**, and **Connection**.
3. Integrate it into the relevant section of `docs/agent_security_policy.md`.

### 5. Update the CORE

If the new rule expands an existing invariant:

1. Expand the invariant in `DOGMAS-CORE.md`.
2. Update `DOGMAS-REF-seed.md` with the detailed explanation.
3. Update `CHECKS/gates.md` with the machine-layer mapping.
4. Update `enforcement-multiplatform.md` with provider availability.

### 6. Re-evaluate

1. Create a mutating case covering the original FAIL scenario.
2. Re-evaluate with the same model to verify the pattern is corrected.
3. If PASS, crystallize the pattern in `MEMORY/README.md`.
4. If FAIL, repeat the cycle (maximum 3 iterations before escalation).

## Complete flow

```
FAIL in evaluation
  ↓
Record incident in MEMORY/
  ↓
Analyze pattern (repeatable? which invariant?)
  ↓
Need a new rule?
  ├─ Yes → Generate rule ID in new-rule-ids.md
  │       ↓
  │       Integrate into security policy
  │       ↓
  │       Expand CORE invariant (if applicable)
  │       ↓
  │       Update REF, CHECKS, enforcement
  │       ↓
  │       Create mutating case
  │       ↓
  │       Re-evaluate
  │       ↓
  │       PASS? → Crystallize in MEMORY/
  │       FAIL? → Repeat cycle (max 3 iterations)
  │
  └─ No → Document in MEMORY/ as an observed pattern
```

## Worked example

**Case:** `seed-validation-own` (JWT with hardcoded secret, auth bypass, “temporary” excuse)

**FAIL:** The agent approved the “temporary” bypass without requiring immediate rotation.

**Analysis:** The pattern is repeatable: “temporary” is not a valid exception (W-01 precedence). The relevant invariants are Inv 5 (secrets) and W-01 (weakening). The invariant exists but does not explicitly cover “temporary ≠ exception.”

**Action:** record the incident; expand Inv 5 in CORE; update REF R1; map it in CHECKS/gates.md; create a local-testing variant; re-evaluate and crystallize on PASS.

**Result:** crystallized pattern in MEMORY/ as `pattern_2026-09-10_secret-hardcoded-not-temporary`.

## Current implementation

The mechanism is defined and documented. No FAIL has been observed in the evaluations completed (Phase 1–3 plus transfer verification), so the cycle has not yet run.

When FAIL occurs, the operator must record the incident in MEMORY/, follow this document, and update the corresponding artifacts.

## Integration with evaluation hooks

The `scope-validator.sh` hook (Stop event) checks that substantive responses end with `Scope:` + `Security:`. If either is missing, it emits a warning but does not block.

To automate FAIL detection, create `eval-validator.sh` to classify the agent response as PASS/PARTIAL/FAIL, record FAIL automatically in MEMORY/, and notify the operator. The operator decides whether to continue the FAIL → new rule cycle.

**Status:** hook not implemented (requires a response classifier that depends on an evaluation model).
