"""Tests for task 3.5 — regression tests for incomplete coverage, mixed
configurations, missing literal evidence, and model disagreement.

The four scenarios MUST be detected by ``detect_degradation`` and each
MUST downgrade the claim scope to ``preliminary``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.claims import DegradedReason, detect_degradation, restrict_claim_for_degraded
from contract.profiles import full_suite_profile


def _v(*, prov: str = "verified", comp: str = "comparable", covered: bool | None = None, evidence_mode: str = "literal", judge: str | None = None) -> dict:
    if covered is None:
        covered = True
    return {
        "provenance_status": prov,
        "comparability": comp,
        "coverage_status": "covered" if covered else "limited",
        "evidence_mode": evidence_mode,
        "cost": {"input_tokens": 0, "output_tokens": 0, "model_calls": 0},
        "judge_classification": judge,
    }


def test_incomplete_coverage_is_detected() -> None:
    results = [_v(covered=True), _v(covered=False)]
    assert detect_degradation(results) == DegradedReason.INCOMPLETE_COVERAGE


def test_mixed_configurations_are_detected() -> None:
    results = [_v(comp="comparable"), _v(comp="non_comparable")]
    assert detect_degradation(results) == DegradedReason.MIXED_CONFIGURATIONS


def test_missing_literal_evidence_is_detected() -> None:
    results = [_v(prov="verified"), _v(prov="limited")]
    assert detect_degradation(results) == DegradedReason.MISSING_LITERAL_EVIDENCE


def test_model_disagreement_is_detected() -> None:
    results = [
        _v(prov="verified"),
        _v(prov="verified"),
        _v(prov="verified", judge="PASS"),
        _v(prov="verified", judge="FAIL"),
    ]
    assert detect_degradation(results) == DegradedReason.MODEL_DISAGREEMENT


def test_incomplete_coverage_downgrades_to_preliminary() -> None:
    decision = restrict_claim_for_degraded([_v(covered=True), _v(covered=False)], full_suite_profile())
    assert decision["verdict"] == "preliminary"
    assert decision["reason"] == DegradedReason.INCOMPLETE_COVERAGE


def test_mixed_configurations_downgrade_to_preliminary() -> None:
    decision = restrict_claim_for_degraded([_v(comp="comparable"), _v(comp="non_comparable")], full_suite_profile())
    assert decision["verdict"] == "preliminary"
    assert decision["reason"] == DegradedReason.MIXED_CONFIGURATIONS


def test_missing_literal_evidence_downgrades_to_preliminary() -> None:
    decision = restrict_claim_for_degraded([_v(prov="verified"), _v(prov="limited")], full_suite_profile())
    assert decision["verdict"] == "preliminary"
    assert decision["reason"] == DegradedReason.MISSING_LITERAL_EVIDENCE


def test_model_disagreement_downgrades_to_preliminary() -> None:
    results = [
        _v(prov="verified", judge="PASS"),
        _v(prov="verified", judge="FAIL"),
    ]
    decision = restrict_claim_for_degraded(results, full_suite_profile())
    assert decision["verdict"] == "preliminary"
    assert decision["reason"] == DegradedReason.MODEL_DISAGREEMENT


def test_clean_results_do_not_downgrade() -> None:
    results = [_v(prov="verified"), _v(prov="verified")]
    assert detect_degradation(results) is None
    decision = restrict_claim_for_degraded(results, full_suite_profile())
    assert decision["verdict"] == "pass"
