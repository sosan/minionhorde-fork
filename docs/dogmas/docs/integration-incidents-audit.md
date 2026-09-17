# Integration with `incident_*` and `audit_*`

## Purpose

Document how the dogma system integrates with the `incident_*` and `audit_*` entities of the multi-agent SDLC workflow. These entities provide traceability and persistent memory for security incidents and audits.

## Workflow entities

### `incident_*`

**Owner:** Code Review (per the Document Ownership Map in workflow.md).

**Purpose:** record quality and security incidents discovered during code review.

**Creation phase:** post-review, after Code Review identifies a problem.

**Required by:** future references when prior incidents must be consulted.

**Structure:**
```markdown
### incident_<type>_<date>T<time>
- **Severity:** low | medium | high | critical
- **Category:** security | quality | performance | compliance
- **File:** file where the incident was found
- **Line:** line in the file
- **Description:** incident description
- **Suggestion:** correction suggestion
- **Status:** open | resolved | wontfix
- **Project:** project to which it belongs
```

### `audit_*`

**Owner:** Any agent (any agent may create audit entries).

**Purpose:** record audit events for traceability and compliance.

**Creation phase:** ongoing, throughout the workflow.

**Required by:** PM and Compliance for compliance reports.

**Structure:**
```markdown
### audit_<date>T<time>
- **Timestamp:** event timestamp
- **Start_time:** event start
- **End_time:** event end
- **Duration:** event duration
- **From:** agent that initiated the action
- **To:** agent that received the action
- **Action:** action type (create, read, update, delete, delegate)
- **Target_files:** affected files
- **Status:** success | failure | pending
- **Phase:** workflow phase where it occurred
- **Tier:** workflow tier (0, 1, 2, 3)
```

## Integration with the dogma system

### 1. Incident detection

When `scope-validator.sh` detects a dogma violation (for example, a response without `Scope:` or `Security:`), record an incident:

```markdown
### incident_dogma_violation_<date>T<time>
- **Severity:** low
- **Category:** compliance
- **File:** agent response
- **Line:** N/A
- **Description:** substantive response without security heartbeat (Scope: or Security:)
- **Suggestion:** add the security heartbeat at the end of the response
- **Status:** open
- **Project:** bootstrap-agent-dogmas
```

### 2. Evaluation audit

When a cross-model evaluation runs, record an audit entry using the timestamp, actors, target files, status, phase, and tier shown in the existing audit schema.

### 3. Hook audit

When a hook runs (`audit-log.sh`, `phase-gate.sh`, etc.), record an audit entry with the hook as `From`, the system as `To`, and the affected hook path in `Target_files`.

### 4. Integration with MEMORY/

Incidents and audits are reflected in `MEMORY/README.md`:

```markdown
### incident_<date>_<case>
- **Situation:** case description
- **Decision:** what the agent did
- **Reason:** why the agent made that decision
- **Transfer:** which decision pattern failed

### audit_<date>_evaluation
- **Evaluation:** cross-model evaluation with N models
- **Result:** X PASS, Y PARTIAL, Z FAIL
- **Crystallized patterns:** pattern list
```

## Integration flow

```
Hook detects violation
  ↓
Record incident in MEMORY/
  ↓
Record audit in .claude-opus-5/audit/audit.log
  ↓
Analyze incident
  ↓
Repeatable pattern?
  ├─ Yes → Crystallize in MEMORY/
  │       ↓
  │       Need a new rule?
  │       ├─ Yes → Generate rule ID (docs/ciclo-fail-nueva-regla.md)
  │       └─ No → Document as observed pattern
  │
  └─ No → Document as isolated incident
```

## MCP integration (future)

When Memory MCP is enabled, `incident_*` and `audit_*` entities will synchronize with the knowledge graph using `create_entities`, `search_nodes`, `add_observations`, and `delete_entities`.

**Status:** MCP is not enabled. Integration is currently manual through `MEMORY/` and `.claude-opus-5/audit/audit.log`.

## Validation

To validate the integration: run a cross-model evaluation; verify incidents in `MEMORY/README.md`; verify audits in `.claude-opus-5/audit/audit.log`; verify patterns crystallize; and verify incidents are resolved and documented.

**Status:** integration defined but not validated with MCP enabled.
