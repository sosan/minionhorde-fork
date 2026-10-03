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


# ---------------------------------------------------------------------------
# Task 4.6: challenge provenance (requested/served model, timestamps,
# prompt/context hash, editor authority, rule claims, provisional flags).
# ---------------------------------------------------------------------------


def test_rule_generated_challenge_carries_rule_and_claim_provenance() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.RULE,
        generator_identity="comprehension-rule",
        generator_version="v2",
        generated_model=None,
        generated_sampling=None,
        target_turn="turn-2",
        content_hash=HASH,
        input_claim_hash="c" * 64,
    )
    assert provenance.authority == ChallengeAuthority.RULE
    record = provenance.to_dict()
    assert record["generator_identity"] == "comprehension-rule"
    assert record["input_claim_hash"] == "c" * 64


def test_model_generated_challenge_carries_requested_and_served_identity() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.JUDGE,
        generator_identity="judge-eval",
        generator_version="v1",
        generated_model="fixture-model",          # requested
        served_model="fixture-model",
        generated_sampling={"temperature": 0},
        prompt_context_hash="d" * 64,
        target_turn="turn-3",
        content_hash=HASH,
        generation_timestamp="2026-10-03T00:00:00Z",
    )
    record = provenance.to_dict()
    assert record["requested_model"] == "fixture-model"
    assert record["served_model"] == "fixture-model"
    assert record["prompt_context_hash"] == "d" * 64
    assert record["generation_timestamp"] == "2026-10-03T00:00:00Z"


def test_served_model_mismatch_marks_record_non_comparable() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.JUDGE,
        generator_identity="judge-eval",
        generator_version="v1",
        generated_model="model-a",
        served_model="model-b",
        generated_sampling={"temperature": 0},
        target_turn="turn-3",
        content_hash=HASH,
    )
    assert provenance.served_matches_requested is False


def test_human_edited_challenge_preserves_edit_event_and_editor() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.HUMAN,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="model-a",
        generated_sampling={"temperature": 0},
        target_turn="turn-4",
        content_hash=HASH,
        delivered_content_hash="b" * 64,
        human_edited=True,
        editor_authority="human-reviewer-1",
        edit_or_selection_event="manual_edit",
        evidence_hashes=(HASH, "e" * 64),
    )
    record = provenance.to_dict()
    assert record["editor_authority"] == "human-reviewer-1"
    assert record["edit_or_selection_event"] == "manual_edit"
    assert record["content_changed_in_delivery"] is True
    assert len(record["evidence_hashes"]) == 2


def test_content_changed_without_human_edit_stays_flagged() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.JUDGE,
        generator_identity="judge-eval",
        generator_version="v1",
        generated_model="model-a",
        generated_sampling={"temperature": 0},
        target_turn="turn-5",
        content_hash=HASH,
        delivered_content_hash="b" * 64,
        human_edited=False,
    )
    report = validate_challenge(Challenge(ChallengeObjective.ADVERSARIAL, provenance))
    assert any("delivered" in warning for warning in report["warnings"])


def test_missing_served_model_marks_model_challenge_provisional() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.JUDGE,
        generator_identity="judge-eval",
        generator_version="v1",
        generated_model="model-a",
        served_model=None,
        generated_sampling={"temperature": 0},
        target_turn="turn-6",
        content_hash=HASH,
    )
    report = validate_challenge(Challenge(ChallengeObjective.ADVERSARIAL, provenance))
    assert report["provisional"] is True
    assert any("served model" in warning for warning in report["warnings"])


def test_missing_prompt_context_hash_marks_model_challenge_provisional() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.JUDGE,
        generator_identity="judge-eval",
        generator_version="v1",
        generated_model="model-a",
        served_model="model-a",
        generated_sampling={"temperature": 0},
        target_turn="turn-7",
        content_hash=HASH,
    )
    report = validate_challenge(Challenge(ChallengeObjective.ADVERSARIAL, provenance))
    assert report["provisional"] is True


def test_rule_challenge_without_claim_hash_is_provisional() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.RULE,
        generator_identity="comprehension-rule",
        generator_version="v2",
        generated_model=None,
        generated_sampling=None,
        target_turn="turn-8",
        content_hash=HASH,
    )
    report = validate_challenge(Challenge(ChallengeObjective.CORRECTIVE, provenance))
    assert report["provisional"] is True
    assert any("input_claim_hash" in warning for warning in report["warnings"])


def test_shared_model_family_is_flagged_and_not_independent() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.JUDGE,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="fixture-model",
        served_model="fixture-model",
        generated_sampling={"temperature": 0},
        target_turn="turn-9",
        content_hash=HASH,
        shared_model_family=True,
    )
    challenge = Challenge(ChallengeObjective.CORRECTIVE, provenance)
    report = validate_challenge(challenge)
    assert report["valid"] is False
    assert any("model family" in warning for warning in report["warnings"])
    attribution = attribute_challenge_outcome(challenge, dimension=OutcomeDimension.CORRECTION, outcome="PASS", evidence_linked=True)
    assert attribution["status"] != AttributionStatus.SUPPORTED.value


def test_generator_distinct_from_evaluated_agent_record() -> None:
    provenance = ChallengeProvenance(
        authority=ChallengeAuthority.HUMAN,
        generator_identity="evaluator",
        generator_version="v1",
        generated_model="model-a",
        generated_sampling={"temperature": 0},
        target_turn="turn-10",
        content_hash=HASH,
    )
    evaluated_agent_identity = "agent-under-test"
    assert provenance.generator_identity != evaluated_agent_identity
    assert provenance.generated_model != evaluated_agent_identity
