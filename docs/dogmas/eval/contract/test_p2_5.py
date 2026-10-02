from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_5 import (
    ContaminationLevel,
    HumanLabeledSubset,
    MemoryRetrievalConfig,
    MemoryRetrievalMode,
    ReliabilityBudget,
    cohen_kappa,
    detect_contamination,
    measure_judge_agreement,
    record_thematic_overlap,
    validate_reliability_coverage,
)


def test_human_subset_requires_cases_and_criteria() -> None:
    with pytest.raises(ValueError, match="case_ids"):
        HumanLabeledSubset("subset", (), {}, "criteria")
    with pytest.raises(ValueError, match="selection_criteria"):
        HumanLabeledSubset("subset", ("case-1",), {"case-1": "PASS"}, "")


def test_human_subset_requires_label_for_every_case() -> None:
    with pytest.raises(ValueError, match="missing labels"):
        HumanLabeledSubset("subset", ("case-1", "case-2"), {"case-1": "PASS"}, "random")


def test_human_subset_serializes_selection_metadata() -> None:
    subset = HumanLabeledSubset("subset-1", ("case-1",), {"case-1": "PASS"}, "stratified by domain")
    payload = subset.to_dict()
    assert payload["subset_id"] == "subset-1"
    assert payload["selection_criteria"] == "stratified by domain"


def test_cohen_kappa_perfect_agreement() -> None:
    assert cohen_kappa(["PASS", "FAIL", "PASS"], ["PASS", "FAIL", "PASS"]) == pytest.approx(1.0)


def test_cohen_kappa_requires_equal_lengths() -> None:
    with pytest.raises(ValueError, match="equal length"):
        cohen_kappa(["PASS"], ["PASS", "FAIL"])


def test_judge_agreement_validated_above_threshold() -> None:
    result = measure_judge_agreement(
        ["PASS", "FAIL", "PASS", "PASS"],
        ["PASS", "FAIL", "PASS", "PASS"],
        threshold=0.8,
        min_subset_size=3,
    )
    assert result.validated is True
    assert result.status == "validated"
    assert result.to_dict()["statistic"] == "cohen_kappa"


def test_judge_agreement_below_threshold_is_not_validated() -> None:
    result = measure_judge_agreement(
        ["PASS", "PASS", "PASS", "PASS"],
        ["PASS", "FAIL", "FAIL", "FAIL"],
        threshold=0.8,
        min_subset_size=3,
    )
    assert result.validated is False
    assert result.status == "below_threshold"


def test_judge_agreement_small_subset_is_insufficient() -> None:
    result = measure_judge_agreement(["PASS", "FAIL"], ["PASS", "FAIL"], min_subset_size=3)
    assert result.validated is False
    assert result.status == "insufficient_subset"


def test_exact_contamination_is_hard_and_excludes_claims() -> None:
    result = detect_contamination("case-1", "hash-1", ["hash-1", "hash-2"], detector_identity="sha256", detector_version="1")
    assert result.level == ContaminationLevel.HARD
    assert result.excludes_from_claims is True
    assert result.requires_review is True
    assert result.to_dict()["detector_identity"] == "sha256"


def test_near_duplicate_is_flagged_and_requires_review() -> None:
    result = detect_contamination(
        "case-1",
        "hash-1",
        ["hash-2"],
        similarity_scores={"hash-2": 0.95},
        similarity_threshold=0.9,
        detector_identity="simhash",
        detector_version="2",
    )
    assert result.level == ContaminationLevel.FLAGGED
    assert result.excludes_from_claims is False
    assert result.requires_review is True
    assert result.score == pytest.approx(0.95)


def test_thematic_overlap_does_not_invalidate_transfer() -> None:
    result = record_thematic_overlap("case-1", "episode-1", detector_identity="topic", detector_version="1")
    assert result.level == ContaminationLevel.THEMATIC
    assert result.excludes_from_claims is False
    assert result.requires_review is False


def test_no_contamination_is_explicit() -> None:
    result = detect_contamination("case-1", "hash-1", ["hash-2"], similarity_scores={"hash-2": 0.3})
    assert result.level == ContaminationLevel.NONE
    assert result.reason == "no contamination detected"


def test_similarity_retrieval_requires_score_and_threshold() -> None:
    with pytest.raises(ValueError, match="score and threshold"):
        MemoryRetrievalConfig(MemoryRetrievalMode.SIMILARITY)


def test_memory_retrieval_config_serializes_mode() -> None:
    config = MemoryRetrievalConfig(MemoryRetrievalMode.SIMILARITY, "minhash", "1", 0.8, 0.75)
    assert config.to_dict()["mode"] == "similarity"
    assert config.to_dict()["score"] == 0.8


def test_reliability_budget_requires_positive_counts() -> None:
    with pytest.raises(ValueError, match="positive"):
        ReliabilityBudget(0, 3, 3)


def test_reliability_coverage_sufficient_and_insufficient() -> None:
    budget = ReliabilityBudget(5, 5, 3)
    assert validate_reliability_coverage("recovery", 5, budget)["status"] == "sufficient"
    assert validate_reliability_coverage("stability", 2, budget)["status"] == "insufficient"
    assert validate_reliability_coverage("unknown", 10, budget)["status"] == "unsupported"
