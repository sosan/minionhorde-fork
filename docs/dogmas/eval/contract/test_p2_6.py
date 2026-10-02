from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_6 import (
    AttributionStatus,
    Challenge,
    ChallengeAuthority,
    ChallengeObjective,
    ChallengeProvenance,
    OutcomeDimension,
    attribute_challenge_outcome,
    content_hash,
    validate_challenge,
    validate_objective_consistency,
)


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


def test_corrective_challenge_requires_verified_authority() -> None:
    with pytest.raises(ValueError, match="unverified"):
        Challenge(ChallengeObjective.CORRECTIVE, make_provenance(ChallengeAuthority.UNVERIFIED))


def test_adversarial_challenge_allows_unverified_authority() -> None:
    challenge = Challenge(ChallengeObjective.ADVERSARIAL, make_provenance(ChallengeAuthority.UNVERIFIED))
    assert challenge.objective == ChallengeObjective.ADVERSARIAL


def test_corrective_challenge_supports_correction_only() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    assert challenge.objective_supports_correction is True
    assert challenge.objective_supports_stability is False


def test_adversarial_challenge_supports_stability_only() -> None:
    challenge = Challenge(ChallengeObjective.ADVERSARIAL, make_provenance())
    assert challenge.objective_supports_correction is False
    assert challenge.objective_supports_stability is True


def test_mixed_challenge_supports_both() -> None:
    challenge = Challenge(ChallengeObjective.MIXED, make_provenance())
    assert challenge.objective_supports_correction is True
    assert challenge.objective_supports_stability is True


def test_provenance_requires_generator_metadata() -> None:
    with pytest.raises(ValueError, match="generator"):
        ChallengeProvenance(
            authority=ChallengeAuthority.HUMAN,
            generator_identity="",
            generator_version="v1",
            generated_model="model",
            generated_sampling={},
            target_turn="turn-1",
            content_hash=HASH,
        )


def test_provenance_requires_target_turn() -> None:
    with pytest.raises(ValueError, match="target_turn"):
        ChallengeProvenance(
            authority=ChallengeAuthority.HUMAN,
            generator_identity="evaluator",
            generator_version="v1",
            generated_model="model",
            generated_sampling={},
            target_turn="",
            content_hash=HASH,
        )


def test_provenance_requires_valid_content_hash() -> None:
    with pytest.raises(ValueError, match="content_hash"):
        ChallengeProvenance(
            authority=ChallengeAuthority.HUMAN,
            generator_identity="evaluator",
            generator_version="v1",
            generated_model="model",
            generated_sampling={},
            target_turn="turn-1",
            content_hash="short",
        )


def test_provenance_detects_delivery_change() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.HUMAN,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="model",
        generated_sampling={},
        target_turn="turn-1",
        content_hash=HASH,
        delivered_content_hash="b" * 64,
    )
    assert provenance.content_changed_in_delivery is True


def test_validate_challenge_flags_unverified_authority() -> None:
    challenge = Challenge(ChallengeObjective.ADVERSARIAL, make_provenance(ChallengeAuthority.UNVERIFIED))
    report = validate_challenge(challenge)
    assert report["valid"] is False
    assert "unverified" in report["warnings"][0]


def test_validate_challenge_flags_shared_model_family() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.HUMAN,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="model",
        generated_sampling={},
        target_turn="turn-1",
        content_hash=HASH,
        shared_model_family=True,
    )
    challenge = Challenge(ChallengeObjective.CORRECTIVE, provenance)
    report = validate_challenge(challenge)
    assert report["valid"] is False
    assert "model family" in report["warnings"][0]


def test_validate_challenge_flags_delivery_change_without_human_edit() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.HUMAN,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="model",
        generated_sampling={},
        target_turn="turn-1",
        content_hash=HASH,
        delivered_content_hash="b" * 64,
        human_edited=False,
    )
    challenge = Challenge(ChallengeObjective.CORRECTIVE, provenance)
    report = validate_challenge(challenge)
    assert report["valid"] is False
    assert "delivered" in report["warnings"][0]


def test_validate_challenge_passes_for_clean_corrective() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    report = validate_challenge(challenge)
    assert report["valid"] is True
    assert report["warnings"] == []


def test_attribute_correction_outcome_supported() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.CORRECTION,
        outcome="PASS",
        evidence_linked=True,
    )
    assert result["status"] == AttributionStatus.SUPPORTED.value
    assert result["objective"] == "corrective"


def test_attribute_stability_outcome_not_supported_for_corrective() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.STABILITY,
        outcome="PASS",
        evidence_linked=True,
    )
    assert result["status"] == AttributionStatus.NOT_SUPPORTED.value


def test_attribute_unverified_when_evidence_missing() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.CORRECTION,
        outcome="PASS",
        evidence_linked=False,
    )
    assert result["status"] == AttributionStatus.UNVERIFIED.value


def test_attribute_provisional_when_human_intervened() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    result = attribute_challenge_outcome(
        challenge,
        dimension=OutcomeDimension.CORRECTION,
        outcome="PASS",
        evidence_linked=True,
        human_intervention=True,
    )
    assert result["status"] == AttributionStatus.PROVISIONAL.value


def test_validate_objective_consistency_passes_when_aligned() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    outcomes = [{"dimension": "correction", "outcome": "PASS"}]
    report = validate_objective_consistency(challenge, outcomes)
    assert report["consistent"] is True
    assert report["mismatches"] == []


def test_validate_objective_consistency_detects_mismatch() -> None:
    challenge = Challenge(ChallengeObjective.CORRECTIVE, make_provenance())
    outcomes = [{"dimension": "stability", "outcome": "PASS"}]
    report = validate_objective_consistency(challenge, outcomes)
    assert report["consistent"] is False
    assert len(report["mismatches"]) == 1
