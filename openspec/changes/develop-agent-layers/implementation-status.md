# Implementation Status and Remaining Roadmap

## Scope

This audit compares `tasks.md` with artifacts currently present in the repository. A task is marked complete only when an implementation artifact and focused validation evidence exist. Similar behavior that does not satisfy the complete task contract remains open.

## Verified completed tasks

The following tasks are now marked `[x]` in `tasks.md`:

- 1.1 — compatibility constraints recorded in `docs/dogmas/eval/COMPATIBILITY.md`.
- 1.2 — versioned schemas exist under `docs/dogmas/eval/schemas/v1/`.
- 1.3 — synthetic fixtures cover complete, interrupted, unverified, and secret-redacted trajectories under `fixtures/valid/trajectory/`; builders and tests in `contract/`.
- 1.4 — schema/fixture validation tests exist and pass.
- 2.1 — Layer A/B serialized profiles (`layer_a_profile.schema.json`, `layer_b_profile.schema.json`, `contract/layer_profiles.py`).
- 2.2 — profile capture integrated into the provenance adapter without weakening enforcement fields.
- 2.3 — Layer C override/irreversible-authorization rejection tests exist and pass.
- 2.4 — learning-loop bounded-budget and no-progress stop checks in `trajectory_runtime.py` with focused tests.
- 3.2 — legacy migration preserves limited provenance and has focused tests.
- 4.3 — safe synthetic calibration/recovery case exists in the vertical slice.
- 4.6 — challenge provenance (generator authority/identity/version, requested and served model, sampling, target turn, challenge/delivered hashes, evidence references, human edit events, shared-model-family flag) recorded on `ChallengeProvenance` with focused tests.
- 5.2 — intentionally recoverable failure case with initial/corrected decision, causal evidence, and human intervention record (`contract/recovery.py`).
- 5.3 — prior passing cases re-run after candidate change; candidate fails on confirmed regression only (`contract/regression.py`).
- 5.4 — comprehension/correction/transfer/recovery/stability/regression/human-intervention/token-turn metrics (`contract/metrics.py`).
- 5.5 — behavior tests for transfer failure, successful recovery, regression detection, and no-progress termination exist and pass.
- 5.6 — stability case with unsupported challenge exists and is classified.
- 5.7 — confirmed regression failures contract in `trajectory_runtime.confirm_regression_failures`; edge coverage in `test_5_7_confirm_regression.py` (default threshold, single-run flips unconfirmed, threshold-3, all-pass/all-fail, counts).
- 5.8 — memory-condition contamination marking and transfer exclusion (`contract/memory_contamination.py`).
- 5.9 — sandboxed observable recovery case exists.
- 5.12 — frozen content-hashed regression manifests and unverifiable-result downgrade on missing/mismatched reference (`contract/regression_manifest.py`).
- 5.13 — non-minimal correction detection contract in `trajectory_runtime.detect_non_minimal_correction`; edge coverage in `test_5_13_non_minimal_correction.py` (identical, allowed-only, added/removed keys, multiple extras sorted, no allowed fields).
- 6.6 — memory-injection boundary case exists.
- 7.3 — coverage gates and preliminary claim status are emitted by the manual evaluation path.
- 8.2 — first vertical-slice experiment and acceptance criteria are documented.
- 8.5 — preliminary report distinguishes descriptive evidence and limitations.
- 9.10 — versioned schemas exist and legacy schema remains compatibility-only.
- 10.3 — vertical-slice acceptance criteria are defined and verified.

These completions do not imply that every scenario in the related spec is implemented.

## Remaining high-priority work

### P0 — Provenance and evidence contracts

- 3.1, 3.3–3.6: unify evidence mode, authority, tool outcomes, case language, served identity, and sampling missingness in every result.
- 9.1–9.4: provider-adapter envelope, pair keys, environment-failure outcomes, and explicit legacy migration semantics.
- 9.8, 10.4, 10.11–10.13: evidence hashes, retention, actors, custody lifecycle, and structured human review.

### P1 — Trajectory and recovery integrity

- 4.1–4.5: bounded Socratic state machine, per-turn claims/evidence, and correction-vs-comprehension tests (4.6 challenge provenance now implemented).
- 5.10–5.11: append-only trajectories (5.2–5.5, 5.7, 5.12, 5.13 now verified complete — see "Verified completed tasks").
- 10.12, 10.26–10.27: custody states, ordered appends, crash recovery, and schema-preserving evolution.

### P1 — Versioned memory lifecycle

- 6.1–6.5, 6.7–6.10: candidate records, human promotion gate, rollback/deprecation, contamination detection, episode minimums, dissent handling, and transfer equivalence.
- 10.21–10.24: conflict precedence, injection budgets, redaction audits, and TTL/context revalidation.

### P2 — Transfer, judge, and statistical rigor

- 3.7–3.10, 5.1, 7.2, 7.6–7.9, 10.1–10.2, 10.5–10.10, 10.17–10.20, 10.25: judge controls, transfer variants, human labels, partition policy, contamination calibration, reliability budgets, discriminating power, equivalence, and claim expiry.

## Recommended implementation order

1. Freeze the current manual vertical slice as descriptive baseline.
2. Implement the common evaluation/provenance envelope and evidence custody.
3. Implement the bounded trajectory state machine and append-only integrity.
4. Implement regression manifests and minimal-correction checks.
5. Implement versioned memory candidates with human promotion and contamination gates.
6. Add transfer/judge/statistical controls only after the preceding evidence contracts are stable.

## Non-goals for the next phase

- No automatic dogma promotion.
- No provider integration requirement while metadata remains unavailable.
- No private chain-of-thought persistence.
- No production deployment claim from the current manual evidence.
