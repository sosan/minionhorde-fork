"""P2.5 contracts for calibration, contamination, retrieval, and reliability."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


class ContaminationLevel(StrEnum):
    HARD = "hard"
    FLAGGED = "flagged"
    THEMATIC = "thematic"
    NONE = "none"


class MemoryRetrievalMode(StrEnum):
    EXACT = "exact"
    SIMILARITY = "similarity"
    NONE = "none"


@dataclass(frozen=True)
class HumanLabeledSubset:
    """Predeclared subset for judge calibration."""

    subset_id: str
    case_ids: tuple[str, ...]
    labels: Mapping[str, str]
    selection_criteria: str
    detector_identity: str = "unknown"
    detector_version: str = "unknown"

    def __post_init__(self) -> None:
        if not self.subset_id:
            raise ValueError("subset_id is required")
        if not self.case_ids:
            raise ValueError("case_ids must not be empty")
        if not self.selection_criteria:
            raise ValueError("selection_criteria is required")
        missing = [case_id for case_id in self.case_ids if case_id not in self.labels]
        if missing:
            raise ValueError(f"missing labels for cases: {missing}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "subset_id": self.subset_id,
            "case_ids": list(self.case_ids),
            "labels": dict(self.labels),
            "selection_criteria": self.selection_criteria,
            "detector_identity": self.detector_identity,
            "detector_version": self.detector_version,
        }


@dataclass(frozen=True)
class KappaAgreement:
    """Cohen's kappa measurement against a human-labeled subset."""

    statistic: str
    threshold: float
    min_subset_size: int
    observed: float
    expected: float
    kappa: float
    n: int
    validated: bool

    @property
    def status(self) -> str:
        if self.n < self.min_subset_size:
            return "insufficient_subset"
        return "validated" if self.kappa >= self.threshold else "below_threshold"

    def to_dict(self) -> dict[str, Any]:
        return {
            "statistic": self.statistic,
            "threshold": self.threshold,
            "min_subset_size": self.min_subset_size,
            "observed": self.observed,
            "expected": self.expected,
            "kappa": self.kappa,
            "n": self.n,
            "validated": self.validated,
            "status": self.status,
        }


def cohen_kappa(judge_labels: Sequence[str], human_labels: Sequence[str]) -> float:
    """Compute Cohen's kappa for two categorical label sequences."""
    if len(judge_labels) != len(human_labels):
        raise ValueError("label sequences must have equal length")
    if not judge_labels:
        raise ValueError("at least one label pair is required")
    n = len(judge_labels)
    categories = sorted(set(judge_labels) | set(human_labels))
    observed_agreement = sum(j == h for j, h in zip(judge_labels, human_labels)) / n
    expected_agreement = 0.0
    for category in categories:
        judge_proportion = sum(label == category for label in judge_labels) / n
        human_proportion = sum(label == category for label in human_labels) / n
        expected_agreement += judge_proportion * human_proportion
    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1.0 - expected_agreement)


def measure_judge_agreement(
    judge_labels: Sequence[str],
    human_labels: Sequence[str],
    *,
    threshold: float = 0.8,
    min_subset_size: int = 3,
    statistic: str = "cohen_kappa",
) -> KappaAgreement:
    """Measure judge agreement against a human-labeled subset."""
    if statistic != "cohen_kappa":
        raise ValueError("only cohen_kappa is supported")
    kappa = cohen_kappa(judge_labels, human_labels)
    observed = sum(j == h for j, h in zip(judge_labels, human_labels)) / len(judge_labels)
    categories = sorted(set(judge_labels) | set(human_labels))
    expected = 0.0
    for category in categories:
        judge_proportion = sum(label == category for label in judge_labels) / len(judge_labels)
        human_proportion = sum(label == category for label in human_labels) / len(human_labels)
        expected += judge_proportion * human_proportion
    validated = len(judge_labels) >= min_subset_size and kappa >= threshold
    return KappaAgreement(
        statistic=statistic,
        threshold=threshold,
        min_subset_size=min_subset_size,
        observed=observed,
        expected=expected,
        kappa=kappa,
        n=len(judge_labels),
        validated=validated,
    )


@dataclass(frozen=True)
class ContaminationResult:
    case_id: str
    level: ContaminationLevel
    detector_identity: str
    detector_version: str
    score: float | None = None
    threshold: float | None = None
    compared_hashes: tuple[str, str] = ()
    review_authority: str = "unknown"
    reason: str = ""

    @property
    def excludes_from_claims(self) -> bool:
        return self.level == ContaminationLevel.HARD

    @property
    def requires_review(self) -> bool:
        return self.level in {ContaminationLevel.HARD, ContaminationLevel.FLAGGED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "level": self.level.value,
            "detector_identity": self.detector_identity,
            "detector_version": self.detector_version,
            "score": self.score,
            "threshold": self.threshold,
            "compared_hashes": list(self.compared_hashes),
            "review_authority": self.review_authority,
            "reason": self.reason,
            "excludes_from_claims": self.excludes_from_claims,
            "requires_review": self.requires_review,
        }


def detect_contamination(
    case_id: str,
    case_hash: str,
    episode_hashes: Iterable[str],
    *,
    similarity_scores: Mapping[str, float] | None = None,
    similarity_threshold: float = 0.9,
    detector_identity: str = "unknown",
    detector_version: str = "unknown",
) -> ContaminationResult:
    """Detect contamination with tiered outcomes."""
    episode_list = list(episode_hashes)
    if case_hash in episode_list:
        return ContaminationResult(
            case_id,
            ContaminationLevel.HARD,
            detector_identity,
            detector_version,
            reason="exact canonical-content match",
        )
    if similarity_scores:
        highest_score = max(similarity_scores.values())
        if highest_score >= similarity_threshold:
            flagged_episode = max(similarity_scores, key=similarity_scores.get)
            return ContaminationResult(
                case_id,
                ContaminationLevel.FLAGGED,
                detector_identity,
                detector_version,
                score=highest_score,
                threshold=similarity_threshold,
                compared_hashes=(case_hash, flagged_episode),
                reason=f"high similarity {highest_score:.3f} >= {similarity_threshold}",
            )
    return ContaminationResult(
        case_id,
        ContaminationLevel.NONE,
        detector_identity,
        detector_version,
        reason="no contamination detected",
    )


def record_thematic_overlap(
    case_id: str,
    episode_id: str,
    *,
    detector_identity: str = "unknown",
    detector_version: str = "unknown",
) -> ContaminationResult:
    """Record thematic overlap without invalidating transfer."""
    return ContaminationResult(
        case_id,
        ContaminationLevel.THEMATIC,
        detector_identity,
        detector_version,
        compared_hashes=("", episode_id),
        reason="thematic or mechanism overlap only; not contamination",
    )


@dataclass(frozen=True)
class MemoryRetrievalConfig:
    mode: MemoryRetrievalMode
    detector_identity: str = "unknown"
    detector_version: str = "unknown"
    score: float | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        if self.mode == MemoryRetrievalMode.SIMILARITY and (self.score is None or self.threshold is None):
            raise ValueError("similarity mode requires score and threshold")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "detector_identity": self.detector_identity,
            "detector_version": self.detector_version,
            "score": self.score,
            "threshold": self.threshold,
        }


@dataclass(frozen=True)
class CaseMetadata:
    case_id: str
    domain: str
    variant_class: str
    decision_principle: str

    def __post_init__(self) -> None:
        if not self.domain or not self.variant_class or not self.decision_principle:
            raise ValueError("domain, variant_class, and decision_principle are required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "domain": self.domain,
            "variant_class": self.variant_class,
            "decision_principle": self.decision_principle,
        }


@dataclass(frozen=True)
class ReliabilityBudget:
    """Configured repetitions per dimension."""

    recovery_repetitions: int
    stability_repetitions: int
    regression_repetitions: int

    def __post_init__(self) -> None:
        if self.recovery_repetitions < 1 or self.stability_repetitions < 1 or self.regression_repetitions < 1:
            raise ValueError("all repetition counts must be positive")

    def required_repetitions(self, dimension: str) -> int:
        return {
            "recovery": self.recovery_repetitions,
            "stability": self.stability_repetitions,
            "regression": self.regression_repetitions,
        }.get(dimension, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_repetitions": self.recovery_repetitions,
            "stability_repetitions": self.stability_repetitions,
            "regression_repetitions": self.regression_repetitions,
        }


def validate_reliability_coverage(
    dimension: str,
    actual_repetitions: int,
    budget: ReliabilityBudget,
) -> dict[str, Any]:
    """Check whether a dimension meets its reliability budget."""
    required = budget.required_repetitions(dimension)
    if required == 0:
        return {"dimension": dimension, "status": "unsupported", "required": 0, "actual": actual_repetitions}
    sufficient = actual_repetitions >= required
    return {
        "dimension": dimension,
        "status": "sufficient" if sufficient else "insufficient",
        "required": required,
        "actual": actual_repetitions,
    }
