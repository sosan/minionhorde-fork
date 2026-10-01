from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from review import Actor, HumanReview, apply_custody_resolution


def test_review_requires_reviewer_role() -> None:
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    HumanReview(review_id="rev-1", reviewer=reviewer)


def test_review_rejects_non_reviewer_role() -> None:
    producer = Actor(actor_id="p1", role="producer", independence="independent")
    with pytest.raises(ValueError, match="reviewer role"):
        HumanReview(review_id="rev-2", reviewer=producer)


def test_review_rejects_invalid_independence() -> None:
    with pytest.raises(ValueError, match="independence"):
        Actor(actor_id="r1", role="reviewer", independence="invalid")


def test_review_rejects_invalid_state() -> None:
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    with pytest.raises(ValueError, match="state"):
        HumanReview(review_id="rev-3", reviewer=reviewer, state="INVALID")


def test_review_close_and_dissent() -> None:
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    review = HumanReview(review_id="rev-4", reviewer=reviewer)
    review.close(decision="PASS", rationale_hash="a" * 64)
    assert review.state == "CLOSED"
    assert review.dissent is False
    assert review.closed_at is not None


def test_review_escalation_records_dissent() -> None:
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    review = HumanReview(review_id="rev-5", reviewer=reviewer)
    review.escalate(reason="disagreement with classifier")
    assert review.state == "ESCALATED"
    assert review.dissent is True
    assert review.dissent_reason == "disagreement with classifier"


def test_review_supersede() -> None:
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    review = HumanReview(review_id="rev-6", reviewer=reviewer)
    review.close(decision="PASS", rationale_hash="a" * 64)
    review.supersede("rev-7")
    assert review.state == "SUPERSEDED"
    assert review.supersedes_review_id == "rev-7"


def test_review_to_dict_serializes_reviewer() -> None:
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    review = HumanReview(review_id="rev-8", reviewer=reviewer)
    data = review.to_dict()
    assert data["reviewer"]["actor_id"] == "r1"
    assert data["reviewer"]["role"] == "reviewer"


def test_corrupted_custody_invalidates_result() -> None:
    result = {"provenance_status": "verified", "comparability": "comparable", "classification_authority": "rule"}
    resolution = {"state": "CORRUPTED"}
    updated = apply_custody_resolution(result, resolution)
    assert updated["evaluation_validity"] == "invalidated"
    assert updated["provenance_status"] == "unverified"
    assert updated["comparability"] == "non_comparable"


def test_expired_literal_downgrades_to_hash_only() -> None:
    result = {"provenance_status": "verified", "evidence_mode": "literal"}
    resolution = {"state": "OPEN", "literal_expired": True}
    updated = apply_custody_resolution(result, resolution)
    assert updated["evaluation_validity"] == "limited"
    assert updated["evidence_mode"] == "hash_only"
    assert updated["provenance_status"] == "limited"


def test_valid_custody_preserves_result() -> None:
    result = {"provenance_status": "verified"}
    resolution = {"state": "OPEN", "literal_expired": False}
    updated = apply_custody_resolution(result, resolution)
    assert updated["evaluation_validity"] == "valid"
    assert updated["provenance_status"] == "verified"
