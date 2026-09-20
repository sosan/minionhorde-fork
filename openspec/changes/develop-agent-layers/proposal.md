## Why

Minionhorde already has strong control and policy foundations, but its operational-learning layer is not yet a reproducible system. Responses can appear introspective or aligned without proving that the agent understood a criterion, corrected a specific error, transferred the correction to a new context, or recovered without introducing regressions.

This change establishes a verifiable architecture for the three layers: Layer A (control and harness), Layer B (criteria and dogmas), and Layer C (operational learning). It prioritizes traceability and measurable behavior over longer prompts or unsupported claims of alignment.

## What Changes

- Define a layered contract separating tool control, behavioral criteria, and operational learning.
- Add structured trajectory records for prompts, context, memory versions, decisions, evidence, corrections, and observable outcomes.
- Add a Socratic interaction protocol with reformulation, challenge, evidence check, correction, audit, and human-escalation states.
- Add versioned provisional memory with promotion, regression, and deprecation rules.
- Add separate evaluation dimensions for comprehension, correction, transfer, recovery, stability, and regression.
- Add cross-model and cross-context evaluation controls, including baseline comparisons and adversarial cases.
- Strengthen evaluation provenance so reported PASS results distinguish literal evidence, evaluator authority, and unverified claims.
- Preserve existing safety boundaries: no secret persistence, no unsafe tool execution, no automatic promotion of a pattern to a dogma, and no destructive test behavior.

## Capabilities

### New Capabilities
- `layered-agent-control`: Defines the contracts and enforcement boundaries for Layers A and B.
- `operational-learning`: Defines trajectories, Socratic correction, recovery, transfer, and versioned memory for Layer C.
- `evaluation-provenance`: Defines reproducible evaluation records, baselines, evidence authority, and cross-model comparison.

### Modified Capabilities

<!-- No existing OpenSpec capabilities are present in openspec/specs/. -->

## Impact

- Evaluation tooling under `docs/dogmas/eval/`, especially result schemas, runners, validators, metrics, and intersection reports.
- Dogma and memory documentation under `docs/dogmas/`.
- Harness configuration and hooks under `.claude/`, without weakening existing security controls.
- New tests and fixtures for trajectory state transitions, transfer, recovery, provenance, and regression.
- No new external dependency is required by this proposal; provider SDKs remain optional and credentials remain environment-only.

## Approval

- **Status:** approved
- **Approved by:** operator, in-session authorization ("salimos de explore mode, crear un change proposal firmado e ir implementando por fases")
- **Approved on:** 2026-09-20
- **Basis:** design decisions 1–26 in `design.md`, the three specs under `specs/`, and readiness conditions in `tasks.md` section 10; structural validation passes with `openspec validate --all --strict`.
- **Signature:** GPG-signed commit in this repository (`commit.gpgsign=true`).
