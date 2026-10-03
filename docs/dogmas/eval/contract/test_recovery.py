"""Task 5.2: intentionally recoverable failure case with initial decision,
corrected decision, causal evidence, and human intervention."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from recovery import (
    RecoveryOutcome,
    RecoveryRecord,
    recovery_outcome,
    recoverable_failure_fixture,
    validate_recovery,
)


def test_recovery_record_requires_content() -> None:
    with pytest.raises(ValueError, match="case_id"):
        RecoveryRecord(case_id="", initial_decision="block", corrected_decision="allow", causal_evidence=())
    with pytest.raises(ValueError, match="initial_decision"):
        RecoveryRecord(case_id="c-1", initial_decision="", corrected_decision="allow", causal_evidence=())


def test_corrected_decision_must_differ_from_initial() -> None:
    with pytest.raises(ValueError, match="corrected"):
        RecoveryRecord(case_id="c-1", initial_decision="block", corrected_decision="block", causal_evidence=())


def test_self_recovered_requires_causal_evidence() -> None:
    record = RecoveryRecord(case_id="c-1", initial_decision="block", corrected_decision="allow", causal_evidence=())
    assert recovery_outcome(record) == RecoveryOutcome.UNVERIFIED


def test_self_recovered_with_evidence() -> None:
    record = RecoveryRecord(
        case_id="c-1",
        initial_decision="block",
        corrected_decision="allow",
        causal_evidence=("a" * 64,),
    )
    assert recovery_outcome(record) == RecoveryOutcome.SELF_RECOVERED


def test_human_intervention_is_recorded_distinctly() -> None:
    record = RecoveryRecord(
        case_id="c-1",
        initial_decision="block",
        corrected_decision="allow",
        causal_evidence=("a" * 64,),
        human_intervention=True,
    )
    assert recovery_outcome(record) == RecoveryOutcome.HUMAN_ASSISTED


def test_no_correction_is_not_recovery() -> None:
    with pytest.raises(ValueError):
        RecoveryRecord(case_id="c-1", initial_decision="block", corrected_decision="block", causal_evidence=("a" * 64,), human_intervention=True)


def test_recoverable_failure_fixture_is_deterministic_and_safe() -> None:
    fixture = recoverable_failure_fixture()
    assert fixture["case_id"] == "synthetic/recoverable-failure-001"
    assert fixture["initial_decision"] != fixture["corrected_decision"]
    assert fixture["causal_evidence"]
    assert all(len(h) == 64 for h in fixture["causal_evidence"])
    text = str(fixture)
    assert "ghp_" not in text
    assert "sk-" not in text
    assert recoverable_failure_fixture() == fixture


def test_validate_recovery_reports_fields() -> None:
    record = RecoveryRecord(
        case_id="c-1",
        initial_decision="block",
        corrected_decision="allow",
        causal_evidence=("a" * 64,),
        human_intervention=False,
    )
    report = validate_recovery(record)
    assert report["case_id"] == "c-1"
    assert report["outcome"] == "self_recovered"
    assert report["has_initial_decision"] is True
    assert report["has_corrected_decision"] is True
    assert report["has_causal_evidence"] is True