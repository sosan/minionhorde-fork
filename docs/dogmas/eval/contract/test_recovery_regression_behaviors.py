"""Task 5.5: tests for transfer failure, successful recovery, regression
detection, and no-progress termination."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from recovery import RecoveryOutcome, RecoveryRecord, recovery_outcome
from regression import RegressionCandidate, evaluate_regression
from trajectory_runtime import Trajectory, TrajectoryError
from transfer_variants import (
    EquivalenceReview,
    ReviewStatus,
    TransferVariant,
    VariantClass,
)


def test_transfer_failure_is_recorded_when_review_not_approved() -> None:
    variant = TransferVariant(
        variant_id="v-1",
        source_case_id="c-1",
        source_case_hash="a" * 64,
        variant_class=VariantClass.CROSS_DOMAIN,
        target_domain="finance",
        source_domain="security",
        decision_principle="verify-before-trust",
        prompt="prompt",
        prompt_hash="b" * 64,
        mutation_distance=3,
    )
    assert variant.review_status == ReviewStatus.PENDING
    assert variant.transfer_eligible is False
    assert isinstance(variant.transfer_eligible, bool)


def test_transfer_failure_when_cross_domain_shares_memory_domain() -> None:
    variant = TransferVariant(
        variant_id="v-2",
        source_case_id="c-1",
        source_case_hash="a" * 64,
        variant_class=VariantClass.CROSS_DOMAIN,
        target_domain="security",
        source_domain="security",
        decision_principle="verify-before-trust",
        prompt="prompt",
        prompt_hash="b" * 64,
        mutation_distance=3,
        supporting_memory_domains=("security",),
    )
    review = EquivalenceReview(
        reviewer_id="reviewer-1",
        authority="human",
        status=ReviewStatus.APPROVED,
        decision_principle="verify-before-trust",
        rationale_hash="c" * 64,
    )
    variant.attach_review(review)
    assert variant.review_status == ReviewStatus.APPROVED
    # Cross-domain into a memory-supporting domain is not transfer evidence.
    assert variant.transfer_eligible is False


def test_successful_recovery_records_corrected_decision_with_evidence() -> None:
    record = RecoveryRecord(
        case_id="c-recovery",
        initial_decision="allow-unsupported",
        corrected_decision="block",
        causal_evidence=("e" * 64,),
        human_intervention=False,
    )
    assert recovery_outcome(record) == RecoveryOutcome.SELF_RECOVERED
    report = record.to_dict()
    assert report["initial_decision"] == "allow-unsupported"
    assert report["corrected_decision"] == "block"
    assert report["causal_evidence"] == ["e" * 64]


def test_regression_detection_confirmed_via_repeat_runs() -> None:
    candidate = RegressionCandidate(
        candidate_id="cand-r",
        prior_passing_cases=(
            {"case_id": "c-1", "case_version": "v1", "passed": True},
            {"case_id": "c-2", "case_version": "v1", "passed": True},
        ),
    )
    report = evaluate_regression(candidate, {"c-1": [False, False], "c-2": [True, True]})
    assert report["confirmed_regressions"] == ["c-1"]
    assert report["candidate_status"] == "failed"


def test_no_progress_termination_aborts_trajectory() -> None:
    trajectory = Trajectory("traj-np", learning_loop=True, no_progress_limit=2)
    trajectory.transition("INTERPRET", "start")
    trajectory.transition("REFORMULATE", "repeat")
    trajectory.transition("CHALLENGE", "repeat-again")
    with pytest.raises(TrajectoryError, match="no progress"):
        trajectory.transition("EVIDENCE_CHECK", "repeat-third")
    assert trajectory.state == "ABORTED"
    assert trajectory.entries[-1].payload["cause"] == "no_progress_exceeded"