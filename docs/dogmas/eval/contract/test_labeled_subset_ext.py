"""Tests for the extended labeled-subset implementation:

- TC-016..019: JSON Schema validation (contract.labeled_subset.validate_against_schema)
- TC-020..023: append-only judge-agreement audit (contract.audit_judge)
- TC-024..028: temporal pre-declaration criterion 1 (contract.pre_declaration)

Maps to AC-13..AC-21 in docs/specs/labeled-subset-protocol.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contract.p2_5 import HumanLabeledSubset


def _make_subset(
    subset_id: str = "review-opus-5-max-v1",
    case_ids: tuple[str, ...] = ("synthetic/case-01", "synthetic/case-02"),
    labels: dict | None = None,
    selection_criteria: str = "Pre-declared; balanced; ceiling exempt.",
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


# ---------------------------------------------------------------------------
# TC-016 — AC-13: a valid subset passes the schema
# ---------------------------------------------------------------------------


def test_schema_valid_subset() -> None:
    from contract.labeled_subset import validate_against_schema

    verdict = validate_against_schema(_make_subset())
    assert verdict.valid
    assert not verdict.issues


# ---------------------------------------------------------------------------
# TC-017 — AC-14: missing field fails the schema
# ---------------------------------------------------------------------------


def test_schema_missing_field() -> None:
    from contract.labeled_subset import validate_against_schema

    doc = _make_subset().to_dict()
    del doc["detector_version"]
    verdict = validate_against_schema(doc)
    assert not verdict.valid
    assert any(i.code == "schema_invalid" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-018 — AC-15: invalid label enum fails the schema
# ---------------------------------------------------------------------------


def test_schema_invalid_label_enum() -> None:
    from contract.labeled_subset import validate_against_schema

    doc = _make_subset().to_dict()
    doc["labels"]["synthetic/case-01"] = "INVALID"
    verdict = validate_against_schema(doc)
    assert not verdict.valid
    assert any(i.code == "schema_invalid" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-019 — AC-16: dual-role prefix required by validate_subset, not the schema
# ---------------------------------------------------------------------------


def test_schema_accepts_judge_only_prefix() -> None:
    from contract.labeled_subset import validate_against_schema

    doc = _make_subset(subset_id="judge-only-subset-001").to_dict()
    verdict = validate_against_schema(doc)
    assert verdict.valid  # judge-only subsets may omit the review- prefix


def test_dual_role_requires_review_prefix() -> None:
    from contract.labeled_subset import validate_subset

    subset = _make_subset(subset_id="judge-only-subset-001")
    verdict = validate_subset(
        subset,
        condition_for={cid: "C0" for cid in subset.case_ids},
        category_for={cid: "comprehension" for cid in subset.case_ids},
        dual_role=True,
        decision_principle="P",
        variant_class="direct",
    )
    assert not verdict.valid
    assert any(i.code == "dual_role_missing_review_prefix" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-020 — AC-17: audit appends and reads back
# ---------------------------------------------------------------------------


def test_audit_append_and_read(tmp_path: Path) -> None:
    from contract.audit_judge import JudgeAgreementAudit

    audit = JudgeAgreementAudit(tmp_path / "audit.jsonl")
    entry = audit.record_measurement(
        subset_id="review-opus-5-max-v1",
        detector_identity="claude-opus-5-max",
        detector_version="build-abc",
        kappa=0.85,
        n=48,
        threshold=0.8,
        min_subset_size=3,
        validated=True,
    )
    assert entry.sequence == 0
    assert audit.verify_chain()
    payload = audit.read_measurements()[0]
    assert payload["kappa"] == 0.85
    assert payload["validated"] is True


# ---------------------------------------------------------------------------
# TC-021 — AC-18: audit is append-only; a second append extends the chain
# ---------------------------------------------------------------------------


def test_audit_append_only_no_overwrite(tmp_path: Path) -> None:
    from contract.audit_judge import JudgeAgreementAudit

    audit = JudgeAgreementAudit(tmp_path / "audit.jsonl")
    audit.record_measurement(
        subset_id="s1", detector_identity="d", detector_version="v1",
        kappa=0.8, n=3, threshold=0.8, min_subset_size=3, validated=True,
    )
    audit.record_measurement(
        subset_id="s2", detector_identity="d", detector_version="v1",
        kappa=0.7, n=3, threshold=0.8, min_subset_size=3, validated=False,
    )
    assert audit.verify_chain()
    measurements = audit.read_measurements()
    assert len(measurements) == 2
    assert measurements[0]["subset_id"] == "s1"
    assert measurements[1]["subset_id"] == "s2"


# ---------------------------------------------------------------------------
# TC-022 — AC-19: tampering breaks the chain and is detected
# ---------------------------------------------------------------------------


def test_audit_tamper_detected(tmp_path: Path) -> None:
    from contract.audit_judge import JudgeAgreementAudit

    audit = JudgeAgreementAudit(tmp_path / "audit.jsonl")
    audit.record_measurement(
        subset_id="s1", detector_identity="d", detector_version="v1",
        kappa=0.8, n=3, threshold=0.8, min_subset_size=3, validated=True,
    )
    journal = tmp_path / "audit.jsonl"
    original = journal.read_text(encoding="utf-8")
    tampered = original.replace('"kappa": 0.8', '"kappa": 0.99')
    journal.write_text(tampered, encoding="utf-8")

    reloaded = JudgeAgreementAudit(journal)
    # AppendLog recovery marks the tampered entry aborted and drops it from the
    # recovered chain. So after reload: chain is empty, verify_chain() is
    # vacuously True, and the measurement is untrusted (empty + count == 0).
    assert reloaded.recovered_count() == 0
    assert reloaded.read_measurements() == []


# ---------------------------------------------------------------------------
# TC-026..TC-027 — AC-23: wired measure_with_audit records the measurement
# ---------------------------------------------------------------------------


def test_measure_with_audit_wired(tmp_path: Path) -> None:  # TC-026
    from contract.audit_judge import JudgeAgreementAudit, measure_with_audit

    audit = JudgeAgreementAudit(tmp_path / "audit.jsonl")
    agreement, entry = measure_with_audit(
        audit,
        judge_labels=["PASS", "FAIL", "PASS", "PASS"],
        human_labels=["PASS", "FAIL", "PASS", "PASS"],
        subset_id="review-opus-5-max-v1",
        detector_identity="claude-opus-5-max",
        detector_version="build-abc",
        threshold=0.8,
        min_subset_size=3,
    )
    assert agreement.validated
    assert entry.entry_type == "judge_agreement_measurement"
    assert entry.payload["subset_id"] == "review-opus-5-max-v1"
    assert entry.payload["kappa"] == agreement.kappa
    assert entry.payload["validated"] is True
    assert audit.verify_chain()
    assert len(audit.read_measurements()) == 1


def test_measure_with_audit_rejects_mismatch(tmp_path: Path) -> None:  # TC-027
    from contract.audit_judge import JudgeAgreementAudit, measure_with_audit

    audit = JudgeAgreementAudit(tmp_path / "audit.jsonl")
    agreement, _ = measure_with_audit(
        audit,
        judge_labels=["PASS", "FAIL", "PASS", "PASS", "FAIL", "FAIL"],
        human_labels=["PASS", "FAIL", "PASS", "PASS", "FAIL", "FAIL"],
        subset_id="review-opus-5-max-v1",
        detector_identity="claude-opus-5-max",
        detector_version="build-abc",
        threshold=0.8,
        min_subset_size=3,
    )
    # A second measurement with different labels extends the chain; the
    # append-only property holds and the disagreement is recorded, not
    # averaged away.
    agreement2, entry2 = measure_with_audit(
        audit,
        judge_labels=["PASS", "FAIL", "PASS", "PASS", "FAIL", "FAIL"],
        human_labels=["PASS", "FAIL", "PASS", "PASS", "PASS", "PASS"],
        subset_id="review-opus-5-max-v1",
        detector_identity="claude-opus-5-max",
        detector_version="build-abc",
        threshold=0.8,
        min_subset_size=3,
    )
    assert agreement.validated
    assert not agreement2.validated  # disagreement drops below the threshold
    assert entry2.sequence == 1
    assert len(audit.read_measurements()) == 2
    assert audit.verify_chain()


# ---------------------------------------------------------------------------
# TC-023 — AC-20: pre-declaration accepted when declared before judge output
# ---------------------------------------------------------------------------


def test_pre_declaration_accepted_when_ordered(tmp_path: Path) -> None:
    from contract.pre_declaration import PreDeclarationRegistry

    registry = PreDeclarationRegistry(tmp_path / "decl.jsonl")
    registry.declare("review-opus-5-max-v1", declared_at="2026-10-07T09:00:00+00:00")
    verdict = registry.validate_pre_declared(
        "review-opus-5-max-v1",
        judge_first_observed_at="2026-10-07T10:00:00+00:00",
    )
    assert verdict.valid
    assert not verdict.issues


# ---------------------------------------------------------------------------
# TC-024 — AC-21: pre-declaration rejected when judge output predates it
# ---------------------------------------------------------------------------


def test_pre_declaration_rejected_when_judge_first(tmp_path: Path) -> None:
    from contract.pre_declaration import PreDeclarationRegistry

    registry = PreDeclarationRegistry(tmp_path / "decl.jsonl")
    registry.declare("review-opus-5-max-v1", declared_at="2026-10-07T10:00:00+00:00")
    verdict = registry.validate_pre_declared(
        "review-opus-5-max-v1",
        judge_first_observed_at="2026-10-07T09:00:00+00:00",
    )
    assert not verdict.valid
    assert any(i.code == "pre_declared_violation" for i in verdict.issues)


# ---------------------------------------------------------------------------
# TC-025 — AC-22: unknown subset is invalid
# ---------------------------------------------------------------------------


def test_pre_declaration_unknown_subset(tmp_path: Path) -> None:
    from contract.pre_declaration import PreDeclarationRegistry

    registry = PreDeclarationRegistry(tmp_path / "decl.jsonl")
    verdict = registry.validate_pre_declared(
        "never-declared", judge_first_observed_at="2026-10-07T09:00:00+00:00"
    )
    assert not verdict.valid
    assert any(i.code == "pre_declared_unknown" for i in verdict.issues)