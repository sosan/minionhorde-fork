# Technical Planning

> **Tier-aware:** Tier 1 Small / Tier 0: skip — no PLANNING.md creation (see `rules/workflow-protocols.md §Document Ownership Map`). Only Tier 1 Medium/Large and Tier 2 risk Medium/High create this file.

## Technology Stack
| Concern | Choice | Justification |
|---------|--------|---------------|
| Language | {{language}} | {{why, tied to PRD}} |
| Framework | {{framework}} | {{why}} |
| Database | {{database}} | {{why}} |
| Infrastructure | {{infra}} | {{why}} |

## Architectural Decisions
### AD-1: {{Decision title}}
- **Context:** {{problem/constraint being addressed}}
- **Decision:** {{chosen approach}}
- **Justification:** {{PRD requirement(s) referenced}}
- **Consequences:** {{trade-offs, risks}}

### AD-2: {{...}}

## System Architecture & Component Boundaries
- {{Component}} — {{responsibility, boundaries}}
- {{Component}} — {{responsibility, boundaries}}

## Data Flow & Integration Patterns
- {{flow description: how data moves between components}}
- {{integration points: APIs, events, shared stores}}

## Implementation Details for Developer
- {{concrete structure: modules, folders}}
- {{dependency order}}
- {{error handling patterns}}
- {{testing strategy}}

## Scalability Strategy
- {{strategy appropriate to project size — do NOT over-engineer for small/medium projects}}
