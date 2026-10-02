from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_3 import (
    ClaimStatus,
    ClaimValidity,
    Discrimination,
    PreRegisteredInclusion,
    apply_multiplicity,
    classify_discrimination,
    holm_adjust,
    tost_equivalence,
)


def test_discrimination_empty_is_unknown() -> None:
    result = classify_discrimination("case-1", [])
    assert result.discrimination == Discrimination.UNKNOWN
    assert result.n == 0


def test_discrimination_ceiling_and_floor() -> None:
    ceiling = classify_discrimination("case-1", [True] * 20)
    floor = classify_discrimination("case-2", [False] * 20)
    assert ceiling.discrimination == Discrimination.CEILING
    assert floor.discrimination == Discrimination.FLOOR


def test_discrimination_small_sample_is_inert() -> None:
    result = classify_discrimination("case-1", [True, False])
    assert result.discrimination == Discrimination.INERT


def test_discrimination_mixed_repetitions_is_discriminating() -> None:
    result = classify_discrimination("case-1", [True, False, True, False, True, False])
    assert result.discrimination == Discrimination.DISCRIMINATING
    assert result.pass_rate == 0.5


def test_tost_requires_paired_lengths_and_positive_margin() -> None:
    with pytest.raises(ValueError, match="equal length"):
        tost_equivalence([1.0], [1.0, 2.0], margin=0.1)
    with pytest.raises(ValueError, match="positive"):
        tost_equivalence([1.0], [1.0], margin=0)


def test_tost_declares_equivalence_for_tiny_stable_delta() -> None:
    result = tost_equivalence([1.00, 1.01, 0.99, 1.00], [1.0, 1.0, 1.0, 1.0], margin=0.05, seed=11)
    assert result.equivalence is True
    assert result.confidence_interval[0] >= -0.05
    assert result.confidence_interval[1] <= 0.05


def test_tost_rejects_equivalence_for_large_delta() -> None:
    result = tost_equivalence([1.5, 1.6, 1.4, 1.5], [1.0, 1.0, 1.0, 1.0], margin=0.1, seed=11)
    assert result.equivalence is False
    assert result.confidence_interval[0] > 0.1


def test_claim_validity_ttl_expires() -> None:
    created = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    claim = ClaimValidity("claim-1", created, ttl_hours=1)
    assert claim.status == ClaimStatus.INVALIDATED


def test_claim_validity_active_before_ttl() -> None:
    created = datetime.now(timezone.utc).isoformat()
    claim = ClaimValidity("claim-1", created, ttl_hours=1)
    assert claim.status == ClaimStatus.DEFINITIVE


def test_claim_dependency_change_invalidates() -> None:
    claim = ClaimValidity(
        "claim-1",
        datetime.now(timezone.utc).isoformat(),
        served_model="model-a",
        criteria_version="criteria-1",
        memory_version="memory-1",
        policy_version="policy-1",
    )
    assert claim.revalidate_dependencies(
        served_model="model-b",
        criteria_version="criteria-1",
        memory_version="memory-1",
        policy_version="policy-1",
    ) is False
    assert claim.status == ClaimStatus.INVALIDATED
    assert "served_model" in claim.invalidated_by


def test_claim_dependencies_unchanged_remain_valid() -> None:
    claim = ClaimValidity(
        "claim-1",
        datetime.now(timezone.utc).isoformat(),
        served_model="model-a",
        criteria_version="criteria-1",
        memory_version="memory-1",
        policy_version="policy-1",
    )
    assert claim.revalidate_dependencies(
        served_model="model-a",
        criteria_version="criteria-1",
        memory_version="memory-1",
        policy_version="policy-1",
    ) is True


def test_preregistered_inclusion_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="both included and excluded"):
        PreRegisteredInclusion("A_vs_B", "correction", ("case-1",), ("case-1",))


def test_preregistered_inclusion_is_explicit() -> None:
    inclusion = PreRegisteredInclusion(
        "criteria_vs_full",
        "transfer",
        ("case-1", "case-2"),
        ("case-3",),
        "contamination",
    )
    assert inclusion.is_included("case-1") is True
    assert inclusion.is_included("case-3") is False
    assert inclusion.to_dict()["primary_dimension"] == "transfer"


def test_holm_adjustment_controls_secondary_p_values() -> None:
    adjusted = holm_adjust([0.01, 0.04, 0.2])
    assert len(adjusted) == 3
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[1] == pytest.approx(0.08)
    assert adjusted[2] == pytest.approx(0.2)


def test_apply_multiplicity_identifies_primary() -> None:
    result = apply_multiplicity([0.01, 0.04, 0.2], primary_index=0)
    assert result["method"] == "holm"
    assert result["primary_adjusted_p"] == pytest.approx(0.03)
    assert result["significant_at_0.05"] == [0]
