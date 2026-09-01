# Spec: {{feature-slug}} — {{Functionality Name}}

## Metadata
| Field | Value |
|-------|-------|
| Spec ID | `SPEC-{{NNN}}` |
| PRD Ref | `FR-{{N}}` in `docs/PRD.md` |
| Status | `draft | approved | implemented` |
| Priority | `P0 | P1 | P2` |

## 1. Description
{{2-3 lines of context — what this functionality does and why it matters.}}

## 2. Input / Output Contract
### 2.1 Input
| Field | Type | Required | Validation | Example |
|-------|------|----------|------------|---------|
| {{name}} | {{string/number/...}} | {{yes/no}} | {{constraint}} | `{{example}}` |

### 2.2 Output
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| {{name}} | {{type}} | {{meaning}} | `{{example}}` |

## 3. Behavior & Business Rules
- **BR-1:** {{rule — must be testable}}
- **BR-2:** {{rule}}
- **Invariant:** {{must always hold}}

## 4. Error Handling
| Condition | Expected Behavior | HTTP/Status Code | Error Code |
|-----------|-------------------|------------------|------------|
| {{input violates BR-1}} | {{reject with ...}} | `400` | `ERR_VALIDATION` |
| {{resource not found}} | {{...}} | `404` | `ERR_NOT_FOUND` |

## 5. Validation Rules
- **VR-1:** {{constraint — format, range, uniqueness}}
- **VR-2:** {{auth / permission check}}

## 6. Acceptance Criteria (Testable)

### AC-1: {{Acceptance criteria description}}
- **GIVEN** (precondition / system state before action)
- **WHEN** (first trigger)
- **THEN** (single observable outcome)

### AC-2: {{Acceptance criteria description}}
- **GIVEN** ...
- **WHEN** ...
- **THEN** ...

### AC-N: ...
- **GIVEN** ...
- **WHEN** ...
- **THEN** ...

## 7. Integration Points
- **Consumed by:** {{component / endpoint / UI}}
- **Depends on:** {{component / service / table}}
- **External systems:** {{none / external system name}}

## 8. Out of Scope
- {{explicitly not in this spec}}
