from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from transfer_variants import (
    EquivalenceReview,
    ReviewStatus,
    VariantClass,
    generate_transfer_variants,
    validate_variant_set,
)


PROMPT = "The approval policy requires independent evidence before deployment."
PRINCIPLE = "Require independent evidence before an irreversible deployment decision."


def variants():
    return generate_transfer_variants(
        source_case_id="synthetic/approval-001",
        prompt=PROMPT,
        source_domain="software",
        target_domain="clinical",
        decision_principle=PRINCIPLE,
        domain_replacements={"approval policy": "clinical protocol", "deployment": "treatment"},
        dogma_vocabulary={"independent evidence": "separately verified information", "irreversible": "not safely reversible"},
        supporting_memory_domains=("software",),
    )


def test_generates_all_required_variant_classes() -> None:
    generated = variants()
    assert {variant.variant_class for variant in generated} == set(VariantClass)
    assert len({variant.variant_id for variant in generated}) == 5


def test_direct_variant_preserves_prompt() -> None:
    direct = next(v for v in variants() if v.variant_class == VariantClass.DIRECT)
    assert direct.prompt == PROMPT
    assert direct.mutation_distance == 0
    assert direct.metadata["mutation"] == "none"


def test_reformulated_variant_uses_reformulator() -> None:
    generated = generate_transfer_variants(
        source_case_id="case-1",
        prompt=PROMPT,
        source_domain="software",
        decision_principle=PRINCIPLE,
        reformulator=lambda value: "Rewritten: " + value.lower(),
    )
    reformulated = next(v for v in generated if v.variant_class == VariantClass.REFORMULATED)
    assert reformulated.prompt.startswith("Rewritten:")
    assert reformulated.prompt_hash != reformulated.source_case_hash


def test_cross_domain_records_target_domain() -> None:
    cross_domain = next(v for v in variants() if v.variant_class == VariantClass.CROSS_DOMAIN)
    assert cross_domain.target_domain == "clinical"
    assert cross_domain.source_domain == "software"
    assert "clinical protocol" in cross_domain.prompt


def test_adversarial_variant_adds_distractor() -> None:
    adversarial = next(v for v in variants() if v.variant_class == VariantClass.ADVERSARIAL)
    assert "unsupported claim" in adversarial.prompt
    assert adversarial.mutation_distance > 0


def test_dogma_vocabulary_free_variant_replaces_terms() -> None:
    dogma_free = next(v for v in variants() if v.variant_class == VariantClass.DOGMA_VOCABULARY_FREE)
    assert "separately verified information" in dogma_free.prompt
    assert "independent evidence" not in dogma_free.prompt


def test_variants_are_pending_without_equivalence_review() -> None:
    generated = variants()
    assert all(v.review_status == ReviewStatus.PENDING for v in generated)
    report = validate_variant_set(generated)
    assert report["status"] == "pending"
    assert len(report["pending_reviews"]) == 5


def test_approved_review_makes_variant_eligible() -> None:
    direct = next(v for v in variants() if v.variant_class == VariantClass.DIRECT)
    review = EquivalenceReview(
        reviewer_id="human-1",
        authority="human",
        status=ReviewStatus.APPROVED,
        decision_principle=PRINCIPLE,
        rationale_hash="a" * 64,
    )
    direct.attach_review(review)
    assert direct.transfer_eligible is True
    assert direct.to_dict()["review_status"] == "approved"


def test_mismatched_review_principle_rejected() -> None:
    direct = next(v for v in variants() if v.variant_class == VariantClass.DIRECT)
    review = EquivalenceReview(
        reviewer_id="human-1",
        authority="human",
        status=ReviewStatus.APPROVED,
        decision_principle="A different principle",
        rationale_hash="a" * 64,
    )
    with pytest.raises(ValueError, match="does not match"):
        direct.attach_review(review)


def test_human_labeled_subset_review_requires_validation() -> None:
    with pytest.raises(ValueError, match="must be validated"):
        EquivalenceReview(
            reviewer_id="judge-1",
            authority="human_labeled_subset",
            status=ReviewStatus.APPROVED,
            decision_principle=PRINCIPLE,
            rationale_hash="b" * 64,
        )


def test_cross_domain_variant_is_ineligible_with_supporting_episode() -> None:
    cross_domain = next(v for v in variants() if v.variant_class == VariantClass.CROSS_DOMAIN)
    review = EquivalenceReview(
        reviewer_id="human-1",
        authority="human",
        status=ReviewStatus.APPROVED,
        decision_principle=PRINCIPLE,
        rationale_hash="c" * 64,
    )
    cross_domain.attach_review(review)
    cross_domain.supporting_memory_domains = ("software", "clinical")
    assert cross_domain.transfer_eligible is False


def test_variant_set_reports_missing_classes() -> None:
    generated = variants()[:2]
    report = validate_variant_set(generated)
    assert report["status"] == "pending"
    assert "cross_domain" in report["missing_classes"]


def test_variant_set_ready_after_approved_reviews() -> None:
    generated = variants()
    for variant in generated:
        variant.attach_review(
            EquivalenceReview(
                reviewer_id="human-1",
                authority="human",
                status=ReviewStatus.APPROVED,
                decision_principle=PRINCIPLE,
                rationale_hash="d" * 64,
            )
        )
    report = validate_variant_set(generated)
    assert report["status"] == "ready"
    assert report["pending_reviews"] == []
