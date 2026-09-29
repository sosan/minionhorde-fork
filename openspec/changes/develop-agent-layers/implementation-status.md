# Implementation Status and Remaining Roadmap

## Scope

This audit compares `tasks.md` with artifacts currently present in the repository. A task is marked complete only when an implementation artifact and focused validation evidence exist. Similar behavior that does not satisfy the complete task contract remains open.

## Verified completed tasks

The following tasks are now marked `[x]` in `tasks.md`:

- 1.2 — versioned schemas exist under `docs/dogmas/eval/schemas/v1/`.
- 1.4 — schema/fixture validation tests exist and pass.
- 3.2 — legacy migration preserves limited provenance and has focused tests.
- 4.3 — safe synthetic calibration/recovery case exists in the vertical slice.
- 5.6 — stability case with unsupported challenge exists and is classified.
- 5.9 — sandboxed observable recovery case exists.
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

- 4.1–4.6: bounded Socratic state machine, per-turn claims/evidence, challenge provenance, and correction-vs-comprehension tests.
- 5.3–5.5, 5.7, 5.10–5.13: regression manifests, confirmed failures, append-only trajectories, concurrent append safety, and non-minimal correction detection.
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
