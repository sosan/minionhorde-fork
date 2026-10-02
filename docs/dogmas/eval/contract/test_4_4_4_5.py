"""Tests for task 4.4 (comprehension vs correction separation) and 4.5 (repeated prompting without causal change).

These tests verify that the evaluation contract correctly distinguishes:
- Comprehension (understanding the criterion) from Correction (changing behavior with evidence)
- Genuine recovery (with causal evidence) from repeated prompting (without new evidence)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_6 import (
    Challenge,
    ChallengeAuthority,
    ChallengeObjective,
    ChallengeProvenance,
    OutcomeDimension,
    attribute_challenge_outcome,
)
from trajectory_runtime import Trajectory


HASH = "a" * 64


def make_provenance(authority: ChallengeAuthority = ChallengeAuthority.HUMAN) -> ChallengeProvenance:
    return ChallengeProvenance(
        authority=authority,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="model-a",
        generated_sampling={"temperature": 0},
        target_turn="turn-1",
        content_hash=HASH,
    )


# ============================================================================
# Task 4.4: Comprehension vs Correction Separation
# ============================================================================


def test_comprehension_pass_without_correction() -> None:
    """Agent reformulates criterion correctly but does not correct an error."""
    trajectory = Trajectory("traj-4.4-1")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("REFORMULATE", "criterion_reformulated")
    trajectory.transition("COMPLETED", "reformulation_correct")

    snapshot = trajectory.snapshot()
    assert snapshot["state"] == "COMPLETED"
    assert any(turn["state"] == "REFORMULATE" for turn in snapshot["turns"])
    assert snapshot["turns"][-1]["transition_cause"] == "reformulation_correct"


def test_correction_with_valid_evidence() -> None:
    """Agent corrects an error with valid causal evidence."""
    trajectory = Trajectory("traj-4.4-2")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "evidence_supplied")
    trajectory.transition("EVIDENCE_CHECK", "evidence_verified")
    trajectory.transition("CORRECT", "decision_changed_with_evidence")
    trajectory.transition("AUDIT", "correction_verified")
    trajectory.transition("COMPLETED", "correction_pass")

    snapshot = trajectory.snapshot()
    assert snapshot["state"] == "COMPLETED"
    assert any(turn["state"] == "CORRECT" for turn in snapshot["turns"])
    assert snapshot["turns"][-1]["transition_cause"] == "correction_pass"


def test_correction_dimension_not_supported_by_adversarial_objective() -> None:
    """An adversarial challenge cannot attribute a correction outcome."""
    challenge = Challenge(
        ChallengeObjective.ADVERSARIAL,
        make_provenance(),
    )
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.CORRECTION,
        outcome="PASS",
        evidence_linked=True,
    )
    assert result["status"] == "not_supported"


def test_correction_without_evidence_linkage_is_unverified() -> None:
    """A corrective challenge without evidence linkage yields an unverified correction."""
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.CORRECTION,
        outcome="PASS",
        evidence_linked=False,
    )
    assert result["status"] == "unverified"
    assert result["evidence_linked"] is False


def test_comprehension_and_correction_are_independent_dimensions() -> None:
    """Comprehension pass does not imply correction pass."""
    trajectory = Trajectory("traj-4.4-4")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("REFORMULATE", "criterion_reformulated")
    trajectory.transition("COMPLETED", "reformulation_correct")

    snapshot = trajectory.snapshot()
    comprehension_pass = any(turn["state"] == "REFORMULATE" for turn in snapshot["turns"])
    correction_pass = any(turn["state"] == "CORRECT" for turn in snapshot["turns"])

    assert comprehension_pass is True
    assert correction_pass is False


def test_correction_requires_evidence_linkage() -> None:
    """Correction claim requires evidence linkage in trajectory."""
    trajectory = Trajectory("traj-4.4-5")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "unsupported_challenge")
    trajectory.transition("COMPLETED", "no_correction")

    snapshot = trajectory.snapshot()
    assert not any(turn["state"] == "CORRECT" for turn in snapshot["turns"])


# ============================================================================
# Task 4.5: Repeated Prompting Without Causal Change
# ============================================================================


def test_repeated_prompting_without_new_evidence_is_not_recovery() -> None:
    """Repeated prompting without new evidence does not count as recovery."""
    trajectory = Trajectory("traj-4.5-1")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "first_attempt")
    trajectory.transition("EVIDENCE_CHECK", "no_new_evidence")
    trajectory.transition("AUDIT", "no_new_evidence_audit")
    trajectory.transition("CHALLENGE", "second_attempt_same_prompt")
    trajectory.transition("EVIDENCE_CHECK", "still_no_new_evidence")
    trajectory.transition("AUDIT", "still_no_new_evidence_audit")
    trajectory.transition("CHALLENGE", "third_attempt_same_prompt")
    trajectory.transition("COMPLETED", "no_recovery")

    snapshot = trajectory.snapshot()
    challenge_turns = [turn for turn in snapshot["turns"] if turn["state"] == "CHALLENGE"]
    assert len(challenge_turns) == 3
    assert not any(turn["state"] == "CORRECT" for turn in snapshot["turns"])
    assert snapshot["turns"][-1]["transition_cause"] == "no_recovery"


def test_recovery_with_new_causal_evidence_is_valid() -> None:
    """Recovery with new causal evidence is valid."""
    trajectory = Trajectory("traj-4.5-2")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "first_attempt_failed")
    trajectory.transition("EVIDENCE_CHECK", "new_evidence_supplied")
    trajectory.transition("CORRECT", "decision_changed_with_evidence")
    trajectory.transition("AUDIT", "recovery_verified")
    trajectory.transition("COMPLETED", "recovery_pass")

    snapshot = trajectory.snapshot()
    assert any(turn["state"] == "EVIDENCE_CHECK" for turn in snapshot["turns"])
    assert any(turn["state"] == "CORRECT" for turn in snapshot["turns"])
    assert snapshot["turns"][-1]["transition_cause"] == "recovery_pass"


def test_repeated_prompting_without_context_change_is_not_recovery() -> None:
    """Repeated prompting without context change is not recovery."""
    trajectory = Trajectory("traj-4.5-3")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "attempt_1")
    trajectory.transition("EVIDENCE_CHECK", "no_context_change")
    trajectory.transition("AUDIT", "no_context_change_audit")
    trajectory.transition("CHALLENGE", "attempt_2_same_context")
    trajectory.transition("EVIDENCE_CHECK", "still_no_context_change")
    trajectory.transition("AUDIT", "still_no_context_change_audit")
    trajectory.transition("CHALLENGE", "attempt_3_same_context")
    trajectory.transition("COMPLETED", "no_causal_change")

    snapshot = trajectory.snapshot()
    challenge_turns = [turn for turn in snapshot["turns"] if turn["state"] == "CHALLENGE"]
    assert len(challenge_turns) == 3
    assert snapshot["turns"][-1]["transition_cause"] == "no_causal_change"


def test_recovery_requires_evidence_state_transition() -> None:
    """Recovery requires evidence state transition, not just repeated challenges."""
    trajectory = Trajectory("traj-4.5-4")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "attempt_without_evidence")
    trajectory.transition("COMPLETED", "no_evidence_transition")

    snapshot = trajectory.snapshot()
    assert not any(turn["state"] == "EVIDENCE_CHECK" for turn in snapshot["turns"])
    assert not any(turn["state"] == "CORRECT" for turn in snapshot["turns"])


def test_recovery_with_unsupported_challenge_is_stability_not_recovery() -> None:
    """Unsupported challenge targeting correct decision is stability test, not recovery."""
    challenge = Challenge(
        ChallengeObjective.ADVERSARIAL,
        make_provenance(),
    )
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.STABILITY,
        outcome="PASS",
        evidence_linked=True,
    )
    assert result["status"] == "supported"
    assert result["dimension"] == "stability"
