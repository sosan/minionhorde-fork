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
- 3.1 — evaluation results are enriched with evidence, judge, and cost blocks plus a configuration hash over policy/partition-manifest/trajectory hashes (`contract/provenance_enrichment.py`). Coverage: `test_3_1_provenance_enrichment.py`.
- 3.2 — legacy migration preserves limited provenance and has focused tests.
- 3.3 — controlled-condition metadata for base, dogmas, memory, and dogmas_memory_socratic (`contract/controlled_condition.py`); activation validation rejects combinations that contradict the declared condition. Coverage: `test_3_3_controlled_condition.py`.
- 3.4 — validation and metrics report provenance, coverage, dissent, confidence intervals, and cost as separate top-level sections (`contract/metrics_breakdown.py`). Coverage: `test_3_4_metrics_breakdown.py`.
- 3.5 — regression detection for incomplete coverage, mixed configurations, missing literal evidence, and model disagreement downgrades claims to preliminary (`contract/claims.py`). Coverage: `test_3_5_regression_degraded.py`.
- 3.6 — served model, sampling parameters, and case language are recorded per result; comparisons are marked non-comparable when served model or sampling differ (`contract/comparability.py`). Coverage: `test_3_6_comparability.py`.
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
- 7.1 — provider adapters (echo, anthropic, openai) return envelopes validated against `adapter_envelope.schema.json`; secrets are read from env only, never persisted; `contract.providers.envelope_has_secret` detects accidental leaks.
- 7.3 — `contract/coverage_gates.py` gates high-confidence scopes on repetition, provenance, category coverage, contamination, and legacy evidence; downgrade vs block semantics are documented per scope.
- 7.4 — `contract/anonymizer.py` builds anonymized reports: scrubs secret patterns and internal paths, keeps allowed top-level keys, computes prompt and response hashes, defaults to `evidence_mode: hash_only`.
- 7.5 — `contract/safe_runner.py` runs the full safe suite (6 cases × 4 conditions) with the `echo` adapter; emits manifest, envelopes, classifications, anonymized report, and coverage gates; baseline artifacts in `fixtures/baseline-safe-run/` and `docs/dogmas/eval/BASELINE_SAFE_RUN.md`.
- 8.1 — Layer A/B/C boundaries, trajectory states, evaluator authority, memory lifecycle, and rollback semantics are documented in `docs/dogmas/eval/ARCHITECTURE.md`.
- 8.2 — first vertical-slice experiment and acceptance criteria are documented.
- 8.4 — existing hooks (audit-log, redact-output, scope-validator, phase-gate, PreToolUse guard) and the security test suite were verified passing; the single failing test is pre-existing and unrelated. Report in `docs/dogmas/eval/HOOK_AND_SECURITY_VERIFICATION.md`.
- 8.5 — preliminary report distinguishes descriptive evidence and limitations.
- 9.1 — common provider-adapter contract (`providers.py`) returns response text, served model, sampling, usage, latency, request id, and error classification; unsupported metadata is recorded as `unknown`. Validated against `adapter_envelope.schema.json` with secret-leak detection (`envelope_has_secret`).
- 9.2 — `EvaluationResult` schema and `adapt_result` now emit a `missingness` object describing which fields are absent (`served_model`, `sampling`, `evidence_reference`, `policy_hash`, `partition_manifest_hash`, `judge`). Coverage: `test_9_2_record_missingness.py`.
- 9.3 — legacy migration (`legacy_migration.py`) imports legacy results as `legacy_limited` with no causal/transfer/promotion/Layer C eligibility; the legacy `recovery` dimension is preserved as `legacy_recovery` and never merged.
- 9.4 — environment-failure vs model-outcome partition (`outcomes.py`) splits records by `outcome_status` and exposes a model-outcome denominator that excludes environment failures. Coverage: `test_9_4_outcomes.py`.
- 9.5 — `profiles.py` defines `vertical_slice` and `full_suite` profiles; vertical_slice has no promotion authority, full_suite does.
- 9.6 — `restrict_claim(profile, scope)` returns `block` / `preliminary` / `pass`; vertical_slice allows only `candidate` and `dimension` (always preliminary) and blocks every other scope. Coverage: `test_9_5_9_6_profiles.py`.
- 9.7 — scenario fixtures (`fixtures.py`): `pair_key_fixture`, `retry_after_failure_fixture`, `environment_failure_fixture`, `claim_scope_downgrade_fixture`, plus the existing `legacy_limited_fixture`. Coverage: `test_9_7_scenarios.py`.
- 9.8 — `provenance_split.py` returns one sha256 hash per role (case, prompt_template, assembled_context, criteria, memory, policy, partition_manifest); `attribute_change` reports the single differing role and raises on multi-role or no-op diffs. Coverage: `test_9_8_provenance_split.py`.
- 9.9 — legacy dimensions preserved separately via `LEGACY_DIMENSION_PREFIX` and `AMBIGUOUS_DIMENSIONS` in `legacy_migration.py`; tests prove `recovery` from a legacy record becomes `legacy_recovery` and never lands in the learning-dimension map.
- 9.10 — versioned schemas exist and legacy schema remains compatibility-only.
- 10.3 — vertical-slice acceptance criteria are defined and verified.
- 10.2 — partition-policy mapping (`vertical_slice` minimal/approved reuse, `full_suite` required growth) is recorded on every partition manifest; `contract/partition_policy.py` plus focused tests in `test_10_2_partition_policy.py`.
- 10.14 — structured Layer C → Layer B amendment proposals (`contract/amendments.py`) require human approval and a regression re-run before `apply_if_stable` may produce a new Layer B profile; coverage in `test_10_14_amendments.py`.
- 10.15 — memory retrieval is recorded per record (`record_retrieval`, `is_empty_retrieval`, `mark_empty_retrieval`, `exclude_empty_retrieval`); empty-retrieval cases under memory conditions are marked `no_memory_retrieved` and excluded from `full_vs_criteria`/`full_vs_memory`. Coverage: `test_10_15_memory_retrieval.py`.
- 10.16 — condition content is verified per record (`memory_injected` vs retrieved content, `criteria_injected` vs criteria hash); mismatches set `outcome_status = condition_mismatch` and the contrast filter excludes them. Coverage: `test_10_16_condition_verification.py`.
- 10.26 — ordered concurrent appends with atomic manifest writes and crash recovery (`contract/append_log.py`): threaded appends serialize through a lock, manifest tampering falls back to a full journal rescan, and incomplete trailing writes are marked aborted. Coverage: `test_10_26_append_log.py`.
- 10.27 — schema versioning with versioned readers and separately hashed migration artifacts (`contract/schema_versions.py`); the original artifact is never mutated and lossy migrations downgrade claim scope to descriptive-only. Coverage: `test_10_27_schema_versions.py`.

These completions do not imply that every scenario in the related spec is implemented.

## Remaining high-priority work

### P0 — Provenance and evidence contracts

- 9.1–9.4: provider-adapter envelope, pair keys, environment-failure outcomes, and explicit legacy migration semantics (9.1–9.4 now verified complete — see "Verified completed tasks").
- 9.8, 10.4, 10.11–10.13: evidence hashes, retention, actors, custody lifecycle, and structured human review.

### P1 — Trajectory and recovery integrity

- 4.1–4.5: bounded Socratic state machine, per-turn claims/evidence, and correction-vs-comprehension tests (4.6 challenge provenance now implemented).
- 5.10–5.11: append-only trajectories (5.2–5.5, 5.7, 5.12, 5.13 now verified complete — see "Verified completed tasks").
- 10.12: custody states (10.26–10.27 ordered appends, crash recovery, and schema-preserving evolution now verified complete — see "Verified completed tasks").

### P1 — Versioned memory lifecycle

- 6.1–6.5, 6.7–6.10: candidate records, human promotion gate, rollback/deprecation, contamination detection, episode minimums, dissent handling, and transfer equivalence.
- 10.21–10.24: conflict precedence, injection budgets, redaction audits, and TTL/context revalidation.

### P2 — Transfer, judge, and statistical rigor

- 3.7–3.10, 5.1, 7.2, 7.6–7.9, 10.1, 10.5–10.10, 10.17–10.20, 10.25: judge controls, transfer variants, human labels, contamination calibration, reliability budgets, discriminating power, equivalence, and claim expiry (10.2 partition-policy mapping now verified complete — see "Verified completed tasks").

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
