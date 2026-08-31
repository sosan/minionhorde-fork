# Implementation Roadmap

> **Tier-aware:** Tier 1 Small / Tier 0: skip — no PLANNING/ROADMAP creation (see `rules/workflow-protocols.md §Document Ownership Map`). Tier 1 Medium/Large: full. Each phase includes `Parallel group` + `Status` for fan-out and `workflow_*` fusion.

## Overview
{{Summary of what will be built and the overall approach}}

## Complexity Assessment
- **Size:** {{small | medium | large}}
- **New files estimated:** {{number}}
- **Existing files to modify:** {{number}}
- **Dependencies:** {{none | few | many}}
- **Integration:** {{internal only | external APIs | both}}

---

## Phase 1: {{Phase Name}}

### Description
{{What this phase delivers — user-facing or internal capability}}

### Files to Create
- `{{src/path/new-file.ts}}` — {{purpose}}
- ...

### Files to Modify
- `{{src/path/existing-file.ts}}` — {{what changes}}
- ...

### Tests Needed
- {{test description 1}}
- {{test description 2}}

### Parallel group
{{A | B | C — same letter = parallelizable (no shared files), different letter = sequential (respects dependencies). See `rules/workflow-protocols.md §Parallelization Protocol` and `§PROJECT_CONTEXT.md Race Condition Prevention`.}}

### Status
{{pending | in_progress | done — updated by PM after group. Fused with `workflow_*` metric (start/end/duration).}}

### Dependencies
- Must complete after: {{none | Phase N | group X}}
- Must complete before: {{Phase N}}

### Estimated Complexity
- {{low | medium | high}}

---

## Phase 2: {{Phase Name}}

### Description
{{...}}

### Files to Create
- ...

### Files to Modify
- ...

### Tests Needed
- ...

### Parallel group
{{A | B | C — same letter = parallelizable}}

### Status
{{pending | in_progress | done}}

### Dependencies
- Must complete after: {{Phase 1 | group A}}
- Must complete before: {{Phase N}}

### Estimated Complexity
- {{low | medium | high}}

---

## Phase 3: {{Phase Name}}
{{Repeat structure for each phase...}}

---

## Implementation Notes
{{Any cross-cutting concerns, shared utilities needed across phases, or architectural decisions that affect implementation order}}
