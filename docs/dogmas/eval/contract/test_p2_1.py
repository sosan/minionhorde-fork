from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_1 import (
    JudgeMetadata,
    RetentionPolicy,
    apply_retention_policy,
    comparison_order,
    paired_mcnemar,
    resolve_evidence_references,
)
from evidence_custody import create_custody


def test_judge_metadata_requires_id() -> None:
    with pytest.raises(ValueError, match="judge_id"):
        JudgeMetadata(judge_id="")


def test_judge_metadata_requires_valid_order() -> None:
    with pytest.raises(ValueError, match="comparison_order"):
        JudgeMetadata(judge_id="j1", comparison_order="random")


def test_judge_metadata_classification_status() -> None:
    provisional = JudgeMetadata(judge_id="j1", agreement_validated=False)
    assert provisional.classification_status == "provisional"
    validated = JudgeMetadata(judge_id="j1", agreement_validated=True)
    assert validated.classification_status == "validated"


def test_judge_metadata_to_dict() -> None:
    judge = JudgeMetadata(judge_id="j1", model_family_relation=False, condition_blinded=True)
    payload = judge.to_dict()
    assert payload["judge_id"] == "j1"
    assert payload["comparison_order"] == "A_then_B"
    assert payload["classification_status"] == "provisional"


def test_comparison_order_is_deterministic() -> None:
    order1 = comparison_order("case-1:rep-1:base")
    order2 = comparison_order("case-1:rep-1:base")
    assert order1 == order2
    assert order1 in {"A_then_B", "B_then_A"}


def test_comparison_order_swap_inverts() -> None:
    original = comparison_order("case-1:rep-1:base")
    swapped = comparison_order("case-1:rep-1:base", swap=True)
    assert swapped != original
    assert {original, swapped} == {"A_then_B", "B_then_A"}


def test_paired_mcnemar_requires_equal_length() -> None:
    with pytest.raises(ValueError, match="equal length"):
        paired_mcnemar([True, True], [True])


def test_paired_mcnemar_requires_nonempty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        paired_mcnemar([], [])


def test_paired_mcnemar_identical_outcomes() -> None:
    outcomes = [True, True, False, False, True]
    result = paired_mcnemar(outcomes, outcomes)
    assert result["discordant_a_wins"] == 0
    assert result["discordant_b_wins"] == 0
    assert result["delta_a_minus_b"] == 0.0
    assert result["concordant"] == len(outcomes)
    assert result["p_value"] == 1.0


def test_paired_mcnemar_discordant_a_wins() -> None:
    a = [True, True, True, False, True]
    b = [True, False, False, False, True]
    result = paired_mcnemar(a, b)
    assert result["discordant_a_wins"] == 2
    assert result["discordant_b_wins"] == 0
    assert result["delta_a_minus_b"] > 0
    assert result["p_value"] < 1.0


def test_paired_mcnemar_confidence_interval() -> None:
    a = [True, True, True, False, True, False, True, True]
    b = [True, False, True, False, True, True, True, False]
    result = paired_mcnemar(a, b, confidence=0.95, bootstrap_runs=500, seed=42)
    assert result["confidence"] == 0.95
    lower, upper = result["confidence_interval"]
    assert lower <= result["delta_a_minus_b"] <= upper


def test_paired_mcnemar_seed_is_reproducible() -> None:
    a = [True, False, True, True, False]
    b = [True, True, False, True, False]
    first = paired_mcnemar(a, b, seed=7)
    second = paired_mcnemar(a, b, seed=7)
    assert first["confidence_interval"] == second["confidence_interval"]


def test_resolve_evidence_references_verified(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("evidence", encoding="utf-8")
    custody = create_custody("custody-1", {"case": artifact})
    result = resolve_evidence_references([custody.artifacts["case"].content_hash], custody)
    assert result["verified"] is True
    assert result["unresolved_hashes"] == []
    assert result["custody_state"] == "OPEN"


def test_resolve_evidence_references_missing(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("evidence", encoding="utf-8")
    custody = create_custody("custody-2", {"case": artifact})
    result = resolve_evidence_references(["deadbeef" * 8], custody)
    assert result["verified"] is False
    assert len(result["unresolved_hashes"]) == 1


def test_resolve_evidence_references_corrupted(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("evidence", encoding="utf-8")
    custody = create_custody("custody-3", {"case": artifact})
    artifact.write_text("modified", encoding="utf-8")
    result = resolve_evidence_references([custody.artifacts["case"].content_hash], custody)
    assert result["custody_state"] == "CORRUPTED"
    assert result["verified"] is False


def test_retention_policy_requires_valid_mode() -> None:
    with pytest.raises(ValueError, match="default_mode"):
        RetentionPolicy(default_mode="invalid")


def test_retention_policy_defaults_to_hash_only() -> None:
    policy = RetentionPolicy()
    assert policy.default_mode == "hash_only"
    assert policy.require_expiry_for_literal is True


def test_apply_retention_policy_corruption_invalidates(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("evidence", encoding="utf-8")
    custody = create_custody("custody-4", {"case": artifact})
    artifact.write_text("tampered", encoding="utf-8")
    result = apply_retention_policy({"evaluation_validity": "valid"}, custody)
    assert result["evaluation_validity"] == "invalidated"
    assert result["evidence"]["custody_state"] == "CORRUPTED"
    assert "CORRUPTED" in result["invalidation_reason"]


def test_apply_retention_policy_literal_expiry(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone
    artifact = tmp_path / "case.txt"
    artifact.write_text("evidence", encoding="utf-8")
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    custody = create_custody("custody-5", {"case": artifact}, literal_expires_at=expired)
    result = apply_retention_policy({"evaluation_validity": "valid", "evidence_mode": "literal"}, custody)
    assert result["evidence_mode"] == "hash_only"
    assert result["evaluation_validity"] == "limited"


def test_apply_retention_policy_preserves_validity_when_healthy(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("evidence", encoding="utf-8")
    custody = create_custody("custody-6", {"case": artifact})
    result = apply_retention_policy({"evaluation_validity": "valid", "evidence_mode": "literal"}, custody)
    assert result["evaluation_validity"] == "limited"
    assert result["evidence"]["custody_state"] == "OPEN"
