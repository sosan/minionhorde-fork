# Evaluation package — Architecture: layers, trajectory, authority, memory, rollback

> Task 8.1 of `openspec/changes/develop-agent-layers`.
> Audit date: 2026-10-06 (branch `feature-bootstrapping`).
> Status: documentation-only. No normative changes to the contract.

This document fixes the conceptual surface that every evaluation record,
trajectory, custody record, and review artifact references. It is the
reference for any future change that touches Layer A, Layer B, Layer C,
trajectory states, evaluator authority, memory lifecycle, or rollback
semantics.

## 1. Layer boundaries

| Layer | Owns | Enforced by | May modify another layer? |
|-------|------|-------------|---------------------------|
| **A — Machine controls** | `tool_permissions`, `secret_redaction`, `audit_logging`, `scope_checks`, `phase_gates`, `irreversible_confirmation` | Hooks in `.claude/hooks/*.sh` + `redact-output.py`; permission policy in `.claude/settings.json` | Never. Authoritative. |
| **B — Normative criteria** | CORE dogmas (DOGMAS-CORE v4.1) + `docs/agent_security_policy.md` | `contract/layer_profiles.LayerBProfile`; guard in `evaluate_recommendation` | May be amended via human-approved Layer C proposals; never auto-applied. |
| **C — Learning layer** | Provisional memory candidates, transfer variants, regression manifests, anonymized reports | `contract/memory_contamination`, `contract.p2_7.MemoryEntry`, `contract/transfer_variants` | May **propose**; never apply to A or B without explicit human approval and a regression re-run. |

### 1.1 Layer A — Machine controls (authoritative)

Layer A is the only layer that actually enforces anything. The controls
declared in `DEFAULT_LAYER_A_CONTROLS` are the harness side:

| Control | Mechanism in this repo | Version |
|---------|------------------------|---------|
| `tool_permissions` | `.claude/settings.json` `permissions.allow` / `permissions.deny` | v1 |
| `secret_redaction` | `.claude/hooks/redact-output.py` (Appendix A regex + entropy heuristic) | v1 |
| `audit_logging` | `.claude/hooks/audit-log.sh` | v1 |
| `scope_checks` | `.claude/hooks/scope-validator.sh` (heartbeat presence in substantive responses) | v1 |
| `phase_gates` | `.claude/hooks/phase-gate.sh` (file integrity checkpoints per phase) | v1 |
| `irreversible_confirmation` | `.claude/hooks/phase-gate.sh` + PreToolUse guard + `.claude/settings.json` deny list | v4.1 (DOGMAS-CORE Inv 2) |

These controls are NEVER weakened, disabled, or bypassed by any record
captured by Layer C. The guard
(`contract/layer_profiles.evaluate_recommendation`) rejects recommendations
whose `action` is `disable_control`, `weaken_redaction`, `bypass_scope_gate`,
or `authorize_irreversible` whenever the corresponding Layer A control is
enabled. This is verified by `contract/test_layer_authority.py` (8 tests).

### 1.2 Layer B — Normative criteria

Layer B holds the rules the contract treats as normative. The default
profile (`default_layer_b_profile`) references:

- DOGMAS-CORE invariants: INV-1, INV-2, INV-3, INV-4, INV-5, INV-7
  (CORE v4.1). The other invariants are recorded but only INV-1/-2/-3/-4/-5/-7
  are marked `normative=true` in the default profile.
- Security policy rule IDs: `security-policy/I-01`, `security-policy/I-04`
  (per `docs/agent_security_policy.md`).
- One non-normative incident reference: `incident/2026-09-bootstrap-stale`
  (used as background context; not binding on its own).

A Layer B criterion record carries `rule_id`, `version`, `normative`, and
`class` ∈ {`rule`, `incident`, `hypothesis`, `example`}. Only `rule`-class
criteria with `normative=true` are binding on a record.

### 1.3 Layer C — Learning layer (proposes, never applies)

Layer C produces **metadata**: trajectory records, custody records,
recovery records, regression manifests, memory candidates, transfer variants,
anonymized reports. None of these may override Layer A or rewrite Layer B.
The guard accepts only:

- `propose_only` — always accepted (no override path).
- `modify_layer_b` — only with `requires_human_approval=true`; the record
  remains a proposal until a regression re-run validates the change.

Any other action against a still-enabled Layer A control is rejected and
the rejected field is named in the `GuardDecision`.

## 2. Trajectory states

`contract/trajectory_runtime.STATES` defines the bounded state machine:

```
INIT ─▶ INTERPRET ─▶ REFORMULATE ─▶ CHALLENGE ─▶ EVIDENCE_CHECK
                                                  │
                              ┌───────────────────┴───────────────────┐
                              ▼                                       ▼
                           CORRECT ─▶ AUDIT ─▶ COMPLETED          HUMAN_INPUT
                                                  ▲                   │
                                                  └─────── CHALLENGE ◀┘
                              │                                       │
                              └──────────── INTERRUPTED / ABORTED ◀──┘
```

### 2.1 States and transitions

- `INIT` → `INTERPRET`, `COMPLETED`, `INTERRUPTED`, `ABORTED`
- `INTERPRET` → `REFORMULATE`, `CHALLENGE`, `EVIDENCE_CHECK`, terminal
- `REFORMULATE` → `CHALLENGE`, `EVIDENCE_CHECK`, terminal
- `CHALLENGE` → `EVIDENCE_CHECK`, `CORRECT`, `HUMAN_INPUT`, terminal
- `EVIDENCE_CHECK` → `CORRECT`, `AUDIT`, `HUMAN_INPUT`, terminal
- `CORRECT` → `AUDIT`, `CHALLENGE`, `EVIDENCE_CHECK`, terminal
- `HUMAN_INPUT` → `INTERPRET`, `EVIDENCE_CHECK`, `AUDIT`, terminal
- `AUDIT` → `COMPLETED`, `CHALLENGE`, `HUMAN_INPUT`, `INTERRUPTED`

The terminal set is `{COMPLETED, INTERRUPTED, ABORTED}`. Once terminal,
no further transitions are accepted (`TrajectoryError`).

### 2.2 Turn budget and no-progress stop (tasks 2.4, 4.1)

- `max_turns` (default 32) bounds total turn count.
- `no_progress_limit` (default 3) bounds consecutive turns without new
  evidence refs or changed claims.
- The stop checks are **only** active when `learning_loop=True`. A normal
  read-only trajectory is not aborted by repeating the same prompt.
- Aborted turns are recorded as a `state` append entry; the entry chain
  remains hash-verifiable.

### 2.3 Per-turn record (task 5.10)

Each `Turn` carries: `turn_id`, `sequence`, `state`, `transition_cause`,
`claims`, `facts`, `inferences`, `assumptions`, `uncertainties`,
`challenges`, `changed_claims`, `preserved_claims`, `evidence_refs`,
`evidence_linked`, `created_at`. A turn with no evidence refs and no
changed claims is treated as no-progress; corrections recorded without
`evidence_linked` are flagged `unverified` by downstream metrics.

### 2.4 Append-only integrity (task 5.11)

`Trajectory.verify_chain()` walks every `AppendEntry` and recomputes the
hash envelope (`sequence`, `entry_type`, `payload`, `previous_hash`). If
any `entry_hash` or `previous_hash` mismatch is found, the trajectory is
considered corrupted and any dependent evaluation must be invalidated.

## 3. Evaluator authority

### 3.1 Producer / classifier / custodian / reviewer (task 10.11)

`contract/review.ACTOR_ROLES` enumerates four roles:

| Role | Responsibility | Independence |
|------|---------------|--------------|
| `producer` | Runs the case; emits the raw record. | `independent` of the classifier and reviewer. |
| `classifier` | Assigns the categorical outcome (PASS/PARTIAL/FAIL). | `independent` of producer. |
| `custodian` | Owns the custody record, freezes / supersedes artifacts. | `independent` of producer and classifier. |
| `reviewer` | Human review of the record. | MUST be `independent`; may `escalate` or `supersede`. |

If two roles coincide or independence is `unknown`, downstream claims are
downgraded by the metrics in `contract/metrics`.

### 3.2 Review states (task 10.13)

`contract/review.REVIEW_STATES` = `{OPEN, ESCALATED, CLOSED, SUPERSEDED}`.
A review carries: `reviewer`, `decision`, `rationale_hash`,
`evidence_blinded`, `dissent`, `dissent_reason`, `closed_at`,
`supersedes_review_id`. A reviewer may `escalate` (record dissent),
`close` with decision+rationale hash, or `supersede` a prior closed
review. Dissent is preserved; cross-model disagreements with equal
served model and sampling are routed to human review, not averaged.

### 3.3 Authority guard (task 2.3)

The Layer C guard rejects proposals that would weaken Layer A controls
or modify Layer B without human approval. This is enforced by code, not
by trust in the model. `contract/test_layer_authority.py` verifies the
guard does not consult `recommendation.justification` to grant an
override.

## 4. Memory lifecycle

`contract/p2_7.MemoryStatus` defines five states:

| Status | Meaning | Eligible for injection? |
|--------|---------|-------------------------|
| `active` | Currently usable. | Yes, subject to budget. |
| `stale` | TTL or context version drift; needs revalidation. | No — excluded from automatic injection. |
| `archived` | Retired, retained for audit. | No. |
| `redacted` | A secret pattern was found and the content was rewritten. | No; recorded as a security event. |
| `conflicted` | Multiple active entries share a `decision_principle` and were not resolvable by priority; escalated to human review. | No, until conflict is resolved. |

### 4.1 Conflict precedence (task 10.21)

`detect_conflicts` groups `active` entries by `decision_principle`,
sorts by `(-priority, entry_id)`, marks the top entry as the tentative
winner, and emits a `ConflictReport` with status `DETECTED` or
`ESCALATED`. Unresolved conflicts block automatic injection; they are
routed to human review per task 10.13.

### 4.2 Injection budget (task 10.22)

`InjectionBudget(max_entries, max_tokens)` caps selection. Entries are
sorted by `(-priority, entry_id)`; any entry whose inclusion would
exceed the cap is pruned. The pruned list, the selected ids, and the
`manifest_hash` are returned. If anything was pruned,
`human_confirmation_required=True` so an operator can adjust the budget
or the priority list.

### 4.3 Redaction and audits (task 10.23)

`redact_secrets` rewrites known secret patterns (`api_key`, `password`,
`private_key`) before storage and marks the entry `redacted`. The
periodic `audit_memory` scan re-runs the same redaction against every
entry and emits `AuditEvent(severity=security, event=secret_detected)`
for any finding.

### 4.4 Revalidation (task 10.24)

`is_stale` returns True when:

- `status` ∈ {`stale`, `archived`, `redacted`} (already non-active); OR
- `expires_at` has passed (TTL); OR
- Any of `model_version`, `criteria_version`, `policy_version`,
  `tooling_version` in the supplied context differs from the value
  recorded at entry creation.

Stale entries are excluded from automatic injection until a revalidation
produces a non-stale determination.

### 4.5 Contamination (task 5.8 / 6.7)

`contract/memory_contamination.mark_memory_condition_contamination`
flags any `memory`-condition result whose `case_id` or `case_hash`
overlaps an active-supported `MemoryEpisode`. Contaminated records are
split out by `exclude_contaminated_from_transfer` and are excluded from
transfer claims. Only the `memory`, `criteria_memory`, and `full`
conditions are eligible for contamination; `criteria` and `base`
conditions never inherit memory state.

## 5. Rollback and supersession

### 5.1 Custody state machine (task 10.12)

`contract/evidence_custody.EvidenceCustody` owns the lifecycle:

```
                ┌─────────── amend (FROZEN only) ─────────┐
                ▼                                          │
OPEN ─freeze ──▶ FROZEN ─supersede ─▶ SUPERSEDED            │
  │                │                                       │
  │                └──── mark_corrupted ───────────────────▶│
  ▼                                                   ▼ ▼ ▼
                  AMENDED                          CORRUPTED
```

| Transition | Allowed from | Effect |
|------------|--------------|--------|
| `freeze()` | `OPEN` | Sets `state=FROZEN`, records `frozen_at`. |
| `amend()` | `FROZEN` | Returns a new record in `AMENDED`; original is retained. |
| `supersede()` | `FROZEN` or `AMENDED` | Sets `state=SUPERSEDED`, records `superseded_at`. |
| `mark_corrupted()` | any except `CORRUPTED` | Sets `state=CORRUPTED`; subsequent `resolve_custody` reports `provenance_status=unverified`. |

`enforce_frozen_immutability` raises `CustodyError` if a caller attempts
to register a role that is already present in a frozen record, or to
mutate any record in `FROZEN`/`AMENDED`/`SUPERSEDED`/`CORRUPTED`.

### 5.2 Resolution and downgrade (task 3.9 / 3.10 / 5.11)

`resolve_custody` is **read-only**: it recomputes artifact hashes and
compares them to the custody record. Outcomes:

- All artifacts present and hash-matching, no expiry → `evidence_mode=literal`,
  `provenance_status=verified`, `evaluation_validity=valid`.
- Stored literal expired → `evidence_mode=hash_only`, `provenance_status=limited`,
  `evaluation_validity=limited`. The literal hash is retained; the content
  is not.
- Any artifact missing or hash-mismatched → custody is marked `CORRUPTED`;
  `provenance_status=unverified`; `evaluation_validity=invalidated`; the
  record is excluded from claims.

`apply_custody_resolution` (in `contract/review.py`) propagates the
resolution into the evaluation result's `evidence_mode`,
`provenance_status`, and `classification_authority` fields so claims
downstream of a corrupted record are auto-blocked.

### 5.3 Memory rollback

Memory rollback is a custody-level action: the superseded memory
version remains in the archive (`status=archived`); a new entry is
created at a new `source_hash`; the active state of the new entry is
gated by `maintenance` and a human confirmation per `apply_injection_budget`.

### 5.4 Trajectory rollback

`Trajectory.amend_turn` only operates on the current turn (the last
turn). Amendments are append-only: a new `turn_amendment` entry is
appended to the chain with the updated payload; older turns remain
immutable. In-place mutation is detected by `verify_chain` and the
trajectory is flagged for invalidation.

### 5.5 Promotion rollback (Layer C → Layer B)

Promotion of a memory candidate to a Layer B amendment requires
`requires_human_approval=True` and a regression re-run. On failure:

- The candidate remains in `active` (or is rolled back to `archived` if
  the operator requests) without being written to Layer B.
- The previous Layer B version is preserved at its `criteria_version`.
- The regression manifest hash used at promotion is retained on the
  record so a future re-run can be reproduced.

## 6. Cross-references

- Hook verification: `docs/dogmas/eval/HOOK_AND_SECURITY_VERIFICATION.md`.
- Compatibility constraints: `docs/dogmas/eval/COMPATIBILITY.md`.
- Safe-suite baseline: `docs/dogmas/eval/BASELINE_SAFE_RUN.md`.
- Schemas: `docs/dogmas/eval/schemas/v1/`.
- Layer A profile implementation: `contract/layer_profiles.py`.
- Trajectory state machine: `contract/trajectory_runtime.py`.
- Memory lifecycle: `contract/p2_7.py`.
- Evidence custody: `contract/evidence_custody.py`.
- Review and authority: `contract/review.py`.
- Hook sources: `.claude/hooks/`.

## 7. Non-goals

This document does not describe:

- Statistical rigor for cross-model claims (see tasks 3.8, 7.7, 10.18).
- The artifact-language policy (task 7.8 / 10.16).
- The legacy schema migration (task 9.3).
- The format-fragility rewording (task 7.9 / 10.9).