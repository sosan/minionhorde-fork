# Labeled Subset Protocol — Implementation Spec

Status: approved for implementation (scope: validation core + tests)

## Purpose

Turn the operator-bound protocol documented in
`docs/dogmas/eval/LABELED_SUBSET_PROTOCOL.md` into enforceable code.
The human labels themselves are operator data and are NOT part of this
spec; the validation machinery that consumes them IS.

## Scope

One core module `contract/labeled_subset.py` + one core test file
`contract/test_labeled_subset.py` covering AC-1..12.

Extension modules (AC-13..22) — added when the deferred non-goals were
implemented:

- `contract/labeled_subset.py::validate_against_schema` — JSON Schema
  gate via `docs/dogmas/eval/schemas/v1/human_labeled_subset.schema.json`.
- `contract/audit_judge.py` — append-only `JudgeAgreementAudit` over
  `AppendLog` (tamper-evident hash chain).
- `contract/pre_declaration.py` — `PreDeclarationRegistry` for
  criterion 1 (temporal pre-declaration).
- `contract/test_labeled_subset_ext.py` — covers AC-13..22.

## Dependencies

- `contract/p2_5.py` — `HumanLabeledSubset`, `detect_contamination`,
  `ContaminationResult`, `ContaminationLevel`.
- `contract/p2_3.py` — `classify_discrimination` (ceiling exemption).
- `contract/profiles.py` — `restrict_claim`, `vertical_slice_profile`,
  `full_suite_profile`.
- `contract/p2_5.py` — `cohen_kappa` (panel check).

## Domain terms

- **Subset** — a `HumanLabeledSubset` instance (operator-provided labels).
- **Issue** — a validation problem with a `severity` (`error`/`warning`)
  and a human-readable message.
- **Verdict** — `valid` / `invalid` + the list of issues.
- **Ceiling dimension** — a case classified `ceiling` by
  `classify_discrimination`, i.e. admits only one outcome by
  construction; exempt from the edge-labels rule.
- **Dual role** — a subset used as review authority for transfer
  variants must be scoped to a `decision_principle` + `variant_class`.
- **Portability** — reuse of a subset across conditions is blocked when
  case or detector changes.

## AC-N (GIVEN/WHEN/THEN)

### AC-1: Field-level validation is inherited from the dataclass
**GIVEN** an empty `subset_id`, empty `case_ids`, or empty
`selection_criteria`
**WHEN** `validate_subset(subset)` runs
**THEN** the verdict is `invalid` with an `error` issue naming the
missing field

### AC-2: Contamination is rejected
**GIVEN** a case whose `case_hash` matches an episode hash (HARD) or
exceeds the similarity threshold (FLAGGED)
**WHEN** `validate_subset(subset, case_hashes={...}, episode_hashes={...})`
runs
**THEN** the verdict is `invalid` with an `error` issue naming the case

### AC-3: Contamination is severity-tiered
**GIVEN** a HARD contamination
**WHEN** validation runs
**THEN** the issue severity is `error`
**GIVEN** a FLAGGED contamination
**WHEN** validation runs
**THEN** the issue severity is `warning`

### AC-4: Condition balance is enforced
**GIVEN** a subset whose labels cover fewer than all declared conditions
**WHEN** validation runs with `expected_conditions=("C0","C1","C2","C3")`
**THEN** the verdict is `invalid` with an `error` issue listing the
missing conditions

### AC-5: Category balance is enforced
**GIVEN** a subset whose case_ids span fewer than 2 distinct dimensions
(categories)
**WHEN** validation runs
**THEN** the verdict is `invalid` with an `error` issue

### AC-6: Edge labels rule with ceiling exemption
**GIVEN** a dimension with both pass and fail outcomes
**WHEN** validation runs with `classify_discrimination` outcomes
**THEN** absence of either label is an `error` issue
**GIVEN** a dimension classified `ceiling` by `classify_discrimination`
**WHEN** validation runs
**THEN** the edge-labels rule is exempt (no issue), on the condition the
subset records the ceiling exemption

### AC-7: Minimum size scales with claim scope
**GIVEN** `min_subset_size=3` (floor) and the size rules
(candidate=48, model=96)
**WHEN** validation runs with `scope="candidate"`
**THEN** a subset of 48 labels passes, fewer fails with an `error`
**GIVEN** `scope="model"`
**WHEN** validation runs
**THEN** 96 labels pass, 48 fail

### AC-8: Profile + scope gate is enforced via restrict_claim
**GIVEN** `vertical_slice@v1` (allows only candidate/dimension)
**WHEN** validation runs with `scope="global"`
**THEN** the verdict is `invalid` with an `error` issue referencing
`restrict_claim` block

### AC-9: Dual-role constraints
**GIVEN** a subset with `subset_id` starting `review-`
**WHEN** validation runs without `decision_principle` and `variant_class`
**THEN** the verdict is `invalid` with an `error`
**GIVEN** a review subset with `decision_principle="P"` and
`variant_class="direct"`
**WHEN** the caller asks to validate a variant with a different principle
**THEN** the verdict is `invalid` with an `error` naming the mismatch

### AC-10: Portability constraints
**GIVEN** a subset whose detector version differs from the frozen
`detector_version`
**WHEN** validation runs with `current_detector_version`
**THEN** the verdict is `invalid` with an `error` naming the mismatch
**GIVEN** a subset whose case content changed (`case_version` bump)
**WHEN** validation runs with `current_case_versions`
**THEN** the verdict is `invalid` with an `error`

### AC-11: Panel disagreement is rejected
**GIVEN** a panel with `inter_labeller_kappa < 0.6`
**WHEN** validation runs with `panel_labels`
**THEN** the verdict is `invalid` with an `error` naming the kappa

### AC-12: Valid subset returns no errors
**GIVEN** a subset passing all criteria with full data
**WHEN** validation runs
**THEN** the verdict is `valid` with an empty issue list

### AC-13: Schema accepts a valid subset
**GIVEN** a subset serialized with `to_dict()` containing all required
fields
**WHEN** `validate_against_schema(doc)` runs
**THEN** the verdict is `valid` with no issues

### AC-14: Schema rejects a missing required field
**GIVEN** a serialized subset missing a required property
**WHEN** `validate_against_schema(doc)` runs
**THEN** the verdict is `invalid` with an `error` issue
(`schema_invalid`)

### AC-15: Schema rejects an invalid label enum
**GIVEN** a serialized subset with a label outside `PASS|FAIL|PARTIAL`
**WHEN** `validate_against_schema(doc)` runs
**THEN** the verdict is `invalid` with an `error` issue
(`schema_invalid`)

### AC-16: Dual-role subset id is prefix-checked
**GIVEN** a judge-only subset whose id omits the `review-` prefix
**WHEN** `validate_against_schema(doc)` runs
**THEN** the verdict is `valid` (the schema permits the prefix, it does
not require it)
**GIVEN** the same subset validated with `dual_role=True`
**WHEN** `validate_subset(...)` runs
**THEN** the verdict is `invalid` with an `error` issue
(`dual_role_missing_review_prefix`)

### AC-17: Agreement measurements are audited append-only
**GIVEN** `record_measurement(...)` with a valid kappa/n/threshold
**WHEN** the audit log is read back
**THEN** the entry is present, `verify_chain()` is `True`, and the
payload round-trips unchanged

### AC-18: Appends extend the chain, never overwrite
**GIVEN** two successive `record_measurement` calls
**WHEN** the audit is read back
**THEN** both entries are present in append order and
`verify_chain()` is `True`

### AC-19: Tampering is detected
**GIVEN** an audit journal whose payload was edited after append
**WHEN** the journal is reloaded
**THEN** the tampered entry is not recovered (`recovered_count() == 0`,
`read_measurements() == []`): hash mismatch marks it aborted

### AC-20: Pre-declaration accepted when declared before judge output
**GIVEN** a subset declared at T1 and judge output first observed at
T2 > T1
**WHEN** `validate_pre_declared(subset_id, judge_first_observed_at=T2)`
runs
**THEN** the verdict is `valid` with no issues

### AC-21: Pre-declaration rejected when judge output predates it
**GIVEN** judge output first observed at T1 and declaration recorded at
T2 > T1
**WHEN** `validate_pre_declared(...)` runs
**THEN** the verdict is `invalid` with an `error` issue
(`pre_declared_violation`)

### AC-22: Unknown subset is not pre-declared
**GIVEN** no declaration record for a subset id
**WHEN** `validate_pre_declared(...)` runs
**THEN** the verdict is `invalid` with an `error` issue
(`pre_declared_unknown`)

## Test scenarios mapping

| AC | Test file | TC |
|----|-----------|----|
| 1 | `test_labeled_subset.py::test_field_validation_missing_fields` | TC-001 |
| 2 | `test_labeled_subset.py::test_contamination_hard_rejected` | TC-002 |
| 3 | `test_labeled_subset.py::test_contamination_tiered_severity` | TC-003 |
| 4 | `test_labeled_subset.py::test_condition_balance_missing` | TC-004 |
| 5 | `test_labeled_subset.py::test_category_balance_single_dimension` | TC-005 |
| 6 | `test_labeled_subset.py::test_edge_labels_missing_pass_or_fail` + `test_ceiling_exemption` | TC-006, TC-007 |
| 7 | `test_labeled_subset.py::test_min_size_scope_scaling` | TC-008 |
| 8 | `test_labeled_subset.py::test_profile_scope_block` | TC-009 |
| 9 | `test_labeled_subset.py::test_dual_role_requires_principle_class` + `test_dual_role_principle_mismatch` | TC-010, TC-011 |
| 10 | `test_labeled_subset.py::test_portability_detector_change` + `test_portability_case_change` | TC-012, TC-013 |
| 11 | `test_labeled_subset.py::test_panel_kappa_below_threshold` | TC-014 |
| 12 | `test_labeled_subset.py::test_valid_subset_no_errors` | TC-015 |
| 13 | `test_labeled_subset_ext.py::test_schema_valid_subset` | TC-016 |
| 14 | `test_labeled_subset_ext.py::test_schema_missing_field` | TC-017 |
| 15 | `test_labeled_subset_ext.py::test_schema_invalid_label_enum` | TC-018 |
| 16 | `test_labeled_subset_ext.py::test_schema_accepts_judge_only_prefix` + `test_dual_role_requires_review_prefix` | TC-019 |
| 17 | `test_labeled_subset_ext.py::test_audit_append_and_read` | TC-020 |
| 18 | `test_labeled_subset_ext.py::test_audit_append_only_no_overwrite` | TC-021 |
| 19 | `test_labeled_subset_ext.py::test_audit_tamper_detected` | TC-022 |
| 20 | `test_labeled_subset_ext.py::test_pre_declaration_accepted_when_ordered` | TC-023 |
| 21 | `test_labeled_subset_ext.py::test_pre_declaration_rejected_when_judge_first` | TC-024 |
| 22 | `test_labeled_subset_ext.py::test_pre_declaration_unknown_subset` | TC-025 |

Coverage: AC→TC is 100% (22 ACs, 25 TCs, no unmapped AC).

## NFR

- No mutation of operator data; `validate_subset` and
  `validate_against_schema` are pure.
- The audit and pre-declaration registries persist only to the
  operator-supplied journal path (append-only, tamper-evident).
- No new dependencies (stdlib + existing contracts only).
- Every public function has a docstring with an example.
- Functions over classes; guard clauses over nesting.

## Non-goals (deferred)

- Creating the actual human labels (`fixtures/human-labeled-subset/`);
  labels remain operator data.
- Enforcing pre-declaration at runtime inside a runner: the temporal
  registry provides the checkpoint, wiring it into a specific runner is
  out of scope here.