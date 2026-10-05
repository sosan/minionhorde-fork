"""Tests for coverage gates (task 7.3)."""

from __future__ import annotations

from typing import Any

import pytest

from contract.coverage_gates import (
    ClaimScope,
    CoverageConfig,
    GateReason,
    GateVerdict,
    emit_gate_blocked_claim,
    evaluate_gate,
    filter_supporting,
)


def _record(
    *,
    case_id: str = "case-01",
    category: str | None = "stability",
    dimension: str | None = "stability",
    provenance_status: str = "verified",
    evidence_mode: str = "literal",
    contaminated: bool = False,
    repetition_count: int = 1,
    classification: str = "PASS",
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "case_id": case_id,
        "classification": classification,
        "provenance_status": provenance_status,
        "evidence_mode": evidence_mode,
        "repetition_id": "r1",
        "repetition_count": repetition_count,
    }
    if category is not None:
        record["category"] = category
    if dimension is not None:
        record["dimension"] = dimension
    if contaminated:
        record["contaminated"] = True
    return record


def test_case_scope_passes_with_minimal_evidence() -> None:
    outcome = evaluate_gate(ClaimScope.CASE, [_record()])
    assert outcome.verdict == GateVerdict.PASS
    assert outcome.reasons == ()


def test_dimension_scope_passes_with_two_distinct_cases() -> None:
    records = [_record(case_id="case-01"), _record(case_id="case-02")]
    outcome = evaluate_gate(ClaimScope.DIMENSION, records)
    assert outcome.verdict == GateVerdict.PASS


def test_global_scope_blocks_when_repetitions_insufficient() -> None:
    outcome = evaluate_gate(
        ClaimScope.GLOBAL,
        [_record()],
        config=CoverageConfig(min_repetitions=3, min_categories=2),
    )
    assert outcome.verdict == GateVerdict.BLOCK
    assert GateReason.REPETITIONS_UNDER in outcome.reasons


def test_global_scope_blocks_when_provenance_insufficient() -> None:
    records = [
        _record(case_id="case-01", category="stability", provenance_status="provisional"),
        _record(case_id="case-02", category="stability", provenance_status="provisional"),
    ]
    outcome = evaluate_gate(ClaimScope.GLOBAL, records, config=CoverageConfig(min_categories=1))
    assert outcome.verdict == GateVerdict.BLOCK
    assert GateReason.PROVENANCE_INSUFFICIENT in outcome.reasons


def test_global_scope_blocks_when_category_coverage_under() -> None:
    records = [
        _record(case_id="case-01", category="stability"),
        _record(case_id="case-02", category="stability"),
    ]
    outcome = evaluate_gate(ClaimScope.GLOBAL, records)
    assert outcome.verdict == GateVerdict.BLOCK
    assert GateReason.CATEGORY_COVERAGE_UNDER in outcome.reasons


def test_contamination_blocks_emission() -> None:
    records = [_record(case_id="case-01"), _record(case_id="case-02", contaminated=True)]
    outcome = evaluate_gate(ClaimScope.MODEL, records)
    assert outcome.verdict == GateVerdict.BLOCK
    assert GateReason.CONTAMINATED_RESULTS in outcome.reasons


def test_legacy_limited_blocks_emission() -> None:
    records = [
        _record(case_id="case-01", evidence_mode="legacy_limited"),
        _record(case_id="case-02"),
    ]
    outcome = evaluate_gate(ClaimScope.MODEL, records)
    assert outcome.verdict == GateVerdict.BLOCK
    assert GateReason.LEGACY_LIMITED in outcome.reasons


def test_high_confidence_scope_records_reason_when_other_reasons_present() -> None:
    records = [_record(case_id="case-01", category="stability")]
    outcome = evaluate_gate(
        ClaimScope.GLOBAL,
        records,
        config=CoverageConfig(min_repetitions=3, min_categories=1),
    )
    assert GateReason.HIGH_CONFIDENCE_SCOPE in outcome.reasons


def test_provenance_provisional_is_preliminary_when_other_conditions_pass() -> None:
    records = [
        _record(case_id="case-01", category="stability", provenance_status="provisional"),
    ]
    cfg = CoverageConfig(min_repetitions=1, min_categories=1, allowed_provenance=("provisional",))
    outcome = evaluate_gate(ClaimScope.CANDIDATE, records, config=cfg)
    assert outcome.verdict == GateVerdict.PRELIMINARY
    assert GateReason.PROVENANCE_INSUFFICIENT in outcome.reasons


def test_filter_supporting_excludes_contaminated_legacy_and_unverified() -> None:
    records = [
        _record(case_id="keep"),
        _record(case_id="drop-contam", contaminated=True),
        _record(case_id="drop-legacy", evidence_mode="legacy_limited"),
        _record(case_id="drop-unverified", provenance_status="unverified"),
    ]
    kept = filter_supporting(records)
    assert [r["case_id"] for r in kept] == ["keep"]


def test_emit_gate_blocked_claim_has_no_claim_field() -> None:
    payload = emit_gate_blocked_claim(ClaimScope.GLOBAL)
    assert payload["claim"] is None
    assert payload["verdict"] == "block"
    assert payload["scope"] == "global"


def test_gate_outcome_to_dict_is_stable() -> None:
    outcome = evaluate_gate(ClaimScope.CASE, [_record()])
    payload = outcome.to_dict()
    assert payload["scope"] == "case"
    assert payload["verdict"] == "pass"
    assert "supporting_cases" in payload
    assert "supporting_categories" in payload


def test_default_config_minimum_repetitions() -> None:
    cfg = CoverageConfig()
    assert cfg.min_repetitions == 2
    assert cfg.min_categories == 2
    assert cfg.allowed_provenance == ("verified", "provisional", "limited")