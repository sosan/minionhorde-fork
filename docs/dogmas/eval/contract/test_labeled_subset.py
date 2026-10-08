"""Tests for contract.labeled_subset — validation core for the
operator-bound human-labeled subset protocol.

Each TC maps to an AC in docs/specs/labeled-subset-protocol.md.
"""

from __future__ import annotations

import pytest

from contract.p2_5 import HumanLabeledSubset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subset(
    subset_id: str = "review-opus-5-max-v1",
    case_ids: tuple[str, ...] = (
        "synthetic/case-01",
        "synthetic/case-02",
        "synthetic/case-03",
        "synthetic/case-04",
        "synthetic/case-05",
        "synthetic/case-06",
        "synthetic/case-07",
        "synthetic/case-08",
    ),
    labels: dict | None = None,
    selection_criteria: str = "Pre-declared; balanced C0-C3; 2 categories; ceiling exempt.",
    detector_identity: str = "claude-opus-5-max",
    detector_version: str = "build-abc",
) -> HumanLabeledSubset:
    if labels is None:
        labels = {cid: "PASS" for cid in case_ids}
    return HumanLabeledSubset(
        subset_id=subset_id,
        case_ids=case_ids,
        labels=labels,
        selection_criteria=selection_criteria,
        detector_identity=detector_identity,
        detector_version=detector_version,
    )


def _balanced_distribution(case_ids: tuple[str, ...]) -> dict[str, str]:
    cond = {0: "C0", 1: "C1", 2: "C2", 3: "C3"}
    return {cid: cond[i % 4] for i, cid in enumerate(case_ids)}


def _category_map(case_ids: tuple[str, ...]) -> dict[str, str]:
    cats = ("comprehension", "correction")
    return {cid: cats[i % 2] for i, cid in enumerate(case_ids)}


# ---------------------------------------------------------------------------
# TC-001 — AC-1: field-level validation
# ---------------------------------------------------------------------------


def test_field_validation_missing_fields() -> None:
    with pytest.raises(ValueError):
        _make_subset(subset_id="")
    with pytest.raises(ValueError):
        _make_subset(case_ids=())
    with pytest.raises(ValueError):
        _make_subset(selection_criteria="")


# ---------------------------------------------------------------------------
# TC-002 — AC-2: HARD contamination is rejected
# ---------------------------------------------------------------------------


def test_contamination_hard_rejected() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset(case_ids=("synthetic/case-A",))
    verdict = validate_subset(
        subset,
        case_hash_for={"synthetic/case-A": "hash-A"},
        episode_hashes={"hash-A"},
    )
    assert not verdict.valid
    assert any(
        i.code == "contamination_hard" and "synthetic/case-A" in i.message
        for i in verdict.issues
    )


# ---------------------------------------------------------------------------
# TC-003 — AC-3: contamination tiered severity
# ---------------------------------------------------------------------------


def test_contamination_tiered_severity(monkeypatch) -> None:
    from contract import labeled_subset
    from contract.p2_5 import ContaminationLevel, ContaminationResult

    subset = _make_subset(case_ids=("synthetic/case-X",))

    def fake_detect(case_id, case_hash, episode_hashes, **kwargs):
        return ContaminationResult(
            case_id=case_id,
            level=ContaminationLevel.FLAGGED,
            detector_identity="det",
            detector_version="v1",
            reason="flagged",
        )

    monkeypatch.setattr(labeled_subset, "detect_contamination", fake_detect)
    verdict = labeled_subset.validate_subset(
        subset,
        case_hash_for={"synthetic/case-X": "hash-X"},
        episode_hashes={"hash-X"},
    )
    flagged = [i for i in verdict.issues if i.code == "contamination_flagged"]
    assert flagged, "expected a flagged-severity issue"
    assert flagged[0].severity == "warning"


# ---------------------------------------------------------------------------
# TC-004 — AC-4: condition balance is enforced
# ---------------------------------------------------------------------------


def test_condition_balance_missing() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset()
    verdict = validate_subset(
        subset,
        condition_for={cid: "C0" for cid in subset.case_ids},
        category_for=_category_map(subset.case_ids),
        expected_conditions=("C0", "C1", "C2", "C3"),
    )
    assert not verdict.valid
    assert any(i.code == "condition_balance_missing" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-005 — AC-5: category balance — fewer than 2 distinct dimensions
# ---------------------------------------------------------------------------


def test_category_balance_single_dimension() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset()
    same_cat = {cid: "comprehension" for cid in subset.case_ids}
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=same_cat,
    )
    assert not verdict.valid
    assert any(i.code == "category_balance_insufficient" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-006 — AC-6: edge labels — missing pass or fail in non-ceiling
# ---------------------------------------------------------------------------


def test_edge_labels_missing_pass_or_fail() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset()
    all_pass = {cid: "PASS" for cid in subset.case_ids}
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=_category_map(subset.case_ids),
        label_for=all_pass,
        discrimination_for={
            "comprehension": ("PASS", "FAIL", "PASS"),
            "correction": ("PASS", "FAIL", "PASS"),
        },
    )
    assert not verdict.valid
    assert any(i.code == "edge_labels_missing_fail" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-007 — AC-6: ceiling exemption
# ---------------------------------------------------------------------------


def test_ceiling_exemption() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset()
    all_pass = {cid: "PASS" for cid in subset.case_ids}
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=_category_map(subset.case_ids),
        label_for=all_pass,
        discrimination_for={
            "comprehension": ("PASS", "PASS", "PASS"),
            "correction": ("PASS", "PASS", "PASS"),
        },
    )
    assert not any(i.code.startswith("edge_labels") for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-008 — AC-7: min size scales with scope
# ---------------------------------------------------------------------------


def test_min_size_scope_scaling() -> None:
    from contract.labeled_subset import validate_subset
    from contract.profiles import full_suite_profile

    profile = full_suite_profile()
    small = _make_subset(
        case_ids=tuple(f"synthetic/c-{i:02d}" for i in range(47)),
        labels={f"synthetic/c-{i:02d}": "PASS" for i in range(47)},
    )
    verdict_small = validate_subset(
        small,
        condition_for=_balanced_distribution(small.case_ids),
        category_for=_category_map(small.case_ids),
        scope="candidate",
        profile=profile,
    )
    assert not verdict_small.valid
    assert any(i.code == "min_size_scope_below_min" for i in verdict_small.issues)

    full = _make_subset(
        case_ids=tuple(f"synthetic/c-{i:02d}" for i in range(48)),
        labels={f"synthetic/c-{i:02d}": "PASS" for i in range(48)},
    )
    verdict_full = validate_subset(
        full,
        condition_for=_balanced_distribution(full.case_ids),
        category_for=_category_map(full.case_ids),
        scope="candidate",
        profile=profile,
    )
    assert not any(i.code == "min_size_scope_below_min" for i in verdict_full.issues)


# ---------------------------------------------------------------------------
# TC-009 — AC-8: profile + scope gate via restrict_claim
# ---------------------------------------------------------------------------


def test_profile_scope_block() -> None:
    from contract.labeled_subset import validate_subset
    from contract.profiles import vertical_slice_profile

    subset = _make_subset()
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=_category_map(subset.case_ids),
        scope="global",
        profile=vertical_slice_profile(),
    )
    assert not verdict.valid
    assert any(i.code == "scope_blocked_by_profile" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-010 — AC-9: dual-role review subset must declare principle + class
# ---------------------------------------------------------------------------


def test_dual_role_requires_principle_class() -> None:
    from contract.labeled_subset import validate_subset

    review_subset = _make_subset(subset_id="review-direct-v1")
    verdict = validate_subset(
        review_subset,
        condition_for=_balanced_distribution(review_subset.case_ids),
        category_for=_category_map(review_subset.case_ids),
        dual_role=True,
        decision_principle="",
        variant_class="direct",
    )
    assert not verdict.valid
    assert any(
        i.code == "dual_role_missing_decision_principle" for i in verdict.issues
    )


# ---------------------------------------------------------------------------
# TC-011 — AC-9: dual-role review subset principle mismatch
# ---------------------------------------------------------------------------


def test_dual_role_principle_mismatch() -> None:
    from contract.labeled_subset import validate_subset

    review_subset = _make_subset(subset_id="review-direct-v1")
    verdict = validate_subset(
        review_subset,
        condition_for=_balanced_distribution(review_subset.case_ids),
        category_for=_category_map(review_subset.case_ids),
        dual_role=True,
        decision_principle="P_other",
        variant_class="direct",
        expected_decision_principle="P_main",
    )
    assert not verdict.valid
    assert any(
        i.code == "dual_role_decision_principle_mismatch" for i in verdict.issues
    )


# ---------------------------------------------------------------------------
# TC-012 — AC-10: portability — detector change invalidates
# ---------------------------------------------------------------------------


def test_portability_detector_change() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset(detector_version="v1")
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=_category_map(subset.case_ids),
        current_detector_version="v2",
    )
    assert not verdict.valid
    assert any(i.code == "portability_detector_version_changed" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-013 — AC-10: portability — case version change invalidates
# ---------------------------------------------------------------------------


def test_portability_case_change() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset()
    current_versions = {cid: "v2" for cid in subset.case_ids}
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=_category_map(subset.case_ids),
        current_case_versions=current_versions,
        subset_case_versions={cid: "v1" for cid in subset.case_ids},
    )
    assert not verdict.valid
    assert any(i.code == "portability_case_version_changed" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-014 — AC-11: panel kappa < 0.6 invalidates
# ---------------------------------------------------------------------------


def test_panel_kappa_below_threshold() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset()
    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(subset.case_ids),
        category_for=_category_map(subset.case_ids),
        panel_labels={
            "human_a": ["PASS", "FAIL"],
            "human_b": ["FAIL", "PASS"],
        },
    )
    assert not verdict.valid
    assert any(i.code == "panel_kappa_below_threshold" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-015 — AC-12: a valid subset returns no errors
# ---------------------------------------------------------------------------


def test_valid_subset_no_errors() -> None:
    from contract.labeled_subset import validate_subset
    from contract.profiles import full_suite_profile

    profile = full_suite_profile()
    n = 96
    case_ids = tuple(f"synthetic/c-{i:02d}" for i in range(n))
    labels = {cid: ("PASS" if i % 3 else "FAIL") for i, cid in enumerate(case_ids)}
    subset = _make_subset(case_ids=case_ids, labels=labels)

    verdict = validate_subset(
        subset,
        condition_for=_balanced_distribution(case_ids),
        category_for=_category_map(case_ids),
        scope="model",
        profile=profile,
        discrimination_for={
            "comprehension": ("PASS", "FAIL", "PASS"),
            "correction": ("PASS", "FAIL", "PASS"),
        },
    )
    assert verdict.valid, verdict
    assert not verdict.issues