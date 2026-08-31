# Spec: {{feature-slug}} — {{Functionality Name}}

## Metadata
| Field | Value |
|-------|-------|
| Spec ID | `SPEC-{{NNN}}` |
| PRD Ref | `FR-{{N}}` in `docs/PRD.md` |
| Status | `draft | approved | implemented` |
| Priority | `P0 | P1 | P2` |
| Owner | `PM` |
| Created | `{{YYYY-MM-DD}}` |
| Depends On | `SPEC-{{NNN}}, SPEC-{{MMM}}` or `none` |
| ADR Ref | `ADR-{{NNN}}` or `none` |

## 1. Description & User Story
**As a** {{actor}} **I want** {{goal}} **so that** {{value}}.
{{2-3 lines of context — what this functionality does and why it matters. Use domain terms from domain-modeling.}}

## 2. Domain Terms (Ubiquitous Language)
| Term | Definition | Source |
|------|------------|--------|
| {{Term}} | {{precise definition}} | `CONTEXT.md` / `PRD` |

## 3. Dependencies & Preconditions
- **Depends on specs:** {{SPEC-XXX — why}}
- **Preconditions:** {{system state before this functionality can run}}
- **ADR ref:** `{{ADR-00N}}` if architectural decision involved

## 4. Input / Output Contract
### 4.1 Input
| Field | Type | Required | Validation | Example |
|-------|------|----------|------------|---------|
| {{name}} | {{string/number/...}} | {{yes/no}} | {{constraint 1}} | `{{example}}` |

**Trigger:** {{API call / event / user action / schedule}}

### 4.2 Output
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| {{name}} | {{type}} | {{meaning}} | `{{example}}` |

**Side effects:** {{DB write / event emitted / external call / none}}
**Idempotency:** {{yes — key is X | no — each call creates new resource}}

## 5. Behavior & Business Rules
- **BR-1:** {{rule — must be testable, single responsibility per clean-code}}
- **BR-2:** {{rule}}
- **Invariant:** {{must always hold, e.g., "balance >= 0"}}

**State transitions (if stateful):**
```text
{{STATE_A}} --{{event}}--> {{STATE_B}} [guard: {{condition}}]
```

## 6. Error Handling
| Condition (When) | Expected Behavior (Then) | HTTP/Status Code | Error Code |
|------------------|--------------------------|------------------|------------|
| {{input violates BR-1}} | {{reject with ...}} | `400` | `ERR_VALIDATION` |
| {{resource not found}} | {{...}} | `404` | `ERR_NOT_FOUND` |

## 7. Validation Rules
- **VR-1:** {{constraint — format, range, uniqueness}}
- **VR-2:** {{auth / permission check}}

## 8. Non-Functional Requirements (for this feature only)
- **Performance:** {{p95 < X ms under Y rps}}
- **Security:** {{authz, data protection}}
- **Observability:** {{log / metric / trace expected — per diagnosing-bugs}}

## 9. Acceptance Criteria (Testable)

> Test Agent creates **one test per AC** before code. Each AC has exactly one observable outcome. Multiple WHEN are sequential steps.

### AC-1: (Acceptance criteria description)
- **GIVEN** (FACT — precondition / system state before action)
- **WHEN** (CONDITION 1 — first trigger)
- **WHEN** (CONDITION 2 — repeat bullet for each additional sequential step, if needed)
- **THEN** (DESIRED RESULT — single observable outcome; combine multiple assertions with "and" inside this one bullet; trace → BR/VR/§6)

### AC-2: (Acceptance criteria description)
- **GIVEN** ...
- **WHEN** ...
- **THEN** ...

### AC-N: ...
- **GIVEN** ...
- **WHEN** ...
- **THEN** ...

**Constraints (enforced by PM checkpoint):**
- `GIVEN` = 1 (exactly one precondition bullet) — if you need multiple facts, combine with "and" inside the single GIVEN
- `WHEN` = 1..n (at least one, multiple allowed for multi-step sequences)
- `THEN` = 1 (exactly one outcome bullet — if you need multiple checks, join with "and" inside the bullet, or split into separate ACs)
- Each `THEN` must be traceable to `BR-N`, `VR-N`, or `§6` row
- Multiple `WHEN` = sequential steps executed in order by the test (not alternatives — use separate AC for alternative paths)

## 10. Test Scenarios Mapping (filled by Test Agent — faithful to ACs, before code)
| Test ID | Acceptance Criteria | Type | File Hint | Status |
|---------|---------------------|------|-----------|--------|
| `TC-001` | `AC-1` | `unit` or `integration` | `tests/{{slug}}.test.ts` | `to-create` |
| `TC-002` | `AC-2` | `unit` | `tests/{{slug}}.test.ts` | `to-create` |

*Gate: 100% of ACs must have a test before Developer starts.*

## 11. Integration Points
- **Consumed by:** {{component / endpoint / UI}}
- **Depends on:** {{component / service / table}}
- **External systems:** {{none / external system name}}

## 12. Out of Scope / Non-Goals
- {{explicitly not in this spec}}

## 13. Open Questions
- [ ] {{question}} — blocks `AC-N` until resolved

## Traceability
| AC | Traces to | Test |
|----|-----------|------|
| AC-1 | `BR-1, VR-1` | `TC-001` |
| AC-2 | `§6 row1, BR-3` | `TC-002` |
