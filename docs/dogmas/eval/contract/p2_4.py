"""P2.4 contracts for cross-model intersection and format fragility."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping, Sequence


class Comparability(StrEnum):
    COMPARABLE = "comparable"
    NON_COMPARABLE = "non_comparable"
    PROVISIONAL = "provisional"


class IntersectionStatus(StrEnum):
    AGREEMENT = "agreement"
    FRONTIER = "frontier"
    UNRESOLVED = "unresolved"
    NON_COMPARABLE = "non_comparable"


@dataclass(frozen=True)
class ConfigurationSignature:
    """Configuration fields that must agree before cross-model comparison."""

    requested_model: str
    served_model: str
    sampling_parameters: Mapping[str, Any]
    case_language: str

    def canonical_sampling(self) -> str:
        return json.dumps(dict(self.sampling_parameters), sort_keys=True, separators=(",", ":"))

    def compare(self, other: "ConfigurationSignature") -> tuple[Comparability, list[str]]:
        differences: list[str] = []
        if self.served_model == "unknown" or other.served_model == "unknown":
            differences.append("served_model_unknown")
        elif self.served_model != other.served_model:
            differences.append("served_model_different")
        if self.canonical_sampling() != other.canonical_sampling():
            differences.append("sampling_different")
        if self.case_language != other.case_language:
            differences.append("case_language_different")
        if differences:
            return Comparability.NON_COMPARABLE, differences
        return Comparability.COMPARABLE, []

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_model": self.requested_model,
            "served_model": self.served_model,
            "sampling_parameters": dict(self.sampling_parameters),
            "case_language": self.case_language,
        }


def configuration_hash(signature: ConfigurationSignature) -> str:
    return hashlib.sha256(json.dumps(signature.to_dict(), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ModelJudgment:
    model_id: str
    outcome: bool | None
    configuration: ConfigurationSignature
    authority: str = "unknown"


@dataclass(frozen=True)
class CaseIntersection:
    case_id: str
    judgments: tuple[ModelJudgment, ...]
    status: IntersectionStatus
    dissenting_models: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status.value,
            "dissenting_models": list(self.dissenting_models),
            "reason": self.reason,
            "judgments": [
                {
                    "model_id": judgment.model_id,
                    "outcome": judgment.outcome,
                    "authority": judgment.authority,
                    "configuration": judgment.configuration.to_dict(),
                }
                for judgment in self.judgments
            ],
        }


def intersect_models(judgments: Sequence[ModelJudgment], *, case_id: str = "unknown") -> CaseIntersection:
    """Intersect model judgments while preserving valid frontier dissent."""
    if not judgments:
        return CaseIntersection(case_id, (), IntersectionStatus.UNRESOLVED, reason="no judgments")
    base = judgments[0].configuration
    differences: list[str] = []
    for judgment in judgments[1:]:
        _, current_differences = base.compare(judgment.configuration)
        differences.extend(current_differences)
    if differences:
        return CaseIntersection(
            case_id,
            tuple(judgments),
            IntersectionStatus.NON_COMPARABLE,
            reason="configuration mismatch: " + ", ".join(dict.fromkeys(differences)),
        )
    observed = {judgment.outcome for judgment in judgments}
    if None in observed or len(observed) == 1:
        status = IntersectionStatus.UNRESOLVED if None in observed else IntersectionStatus.AGREEMENT
        return CaseIntersection(case_id, tuple(judgments), status, reason="missing outcome" if None in observed else "all comparable judgments agree")
    dissenting = tuple(judgment.model_id for judgment in judgments if judgment.outcome != judgments[0].outcome)
    return CaseIntersection(case_id, tuple(judgments), IntersectionStatus.FRONTIER, dissenting, "comparable models disagree; route to human review")


def cross_model_intersection(cases: Mapping[str, Sequence[ModelJudgment]]) -> dict[str, Any]:
    """Build an intersection report without averaging away disagreement."""
    results = [intersect_models(judgments, case_id=case_id) for case_id, judgments in sorted(cases.items())]
    counts = {status.value: sum(result.status == status for result in results) for status in IntersectionStatus}
    return {
        "cases": [result.to_dict() for result in results],
        "counts": counts,
        "frontier_cases": [result.case_id for result in results if result.status == IntersectionStatus.FRONTIER],
        "non_comparable_cases": [result.case_id for result in results if result.status == IntersectionStatus.NON_COMPARABLE],
        "human_review_required": [result.case_id for result in results if result.status in {IntersectionStatus.FRONTIER, IntersectionStatus.UNRESOLVED}],
    }


@dataclass(frozen=True)
class FragilityProtocol:
    rewording_count: int
    sensitivity_threshold: float
    semantic_equivalence_review: str

    def __post_init__(self) -> None:
        if self.rewording_count < 1:
            raise ValueError("rewording_count must be positive")
        if not 0 <= self.sensitivity_threshold <= 1:
            raise ValueError("sensitivity_threshold must be between 0 and 1")
        if not self.semantic_equivalence_review:
            raise ValueError("semantic_equivalence_review is required")


@dataclass(frozen=True)
class FragilityResult:
    original_outcome: bool
    reworded_outcomes: tuple[bool, ...]
    flip_count: int
    sensitivity: float
    status: str
    protocol: FragilityProtocol

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_outcome": self.original_outcome,
            "reworded_outcomes": list(self.reworded_outcomes),
            "flip_count": self.flip_count,
            "sensitivity": self.sensitivity,
            "status": self.status,
            "protocol": {
                "rewording_count": self.protocol.rewording_count,
                "sensitivity_threshold": self.protocol.sensitivity_threshold,
                "semantic_equivalence_review": self.protocol.semantic_equivalence_review,
            },
        }


def measure_format_fragility(
    original_outcome: bool,
    reworded_outcomes: Sequence[bool],
    protocol: FragilityProtocol,
) -> FragilityResult:
    """Measure outcome sensitivity to semantic-preserving rewordings."""
    if len(reworded_outcomes) != protocol.rewording_count:
        raise ValueError("reworded outcome count does not match declared protocol")
    flips = sum(outcome != original_outcome for outcome in reworded_outcomes)
    sensitivity = flips / protocol.rewording_count
    status = "high_fragility" if sensitivity >= protocol.sensitivity_threshold else "low_fragility"
    return FragilityResult(original_outcome, tuple(reworded_outcomes), flips, sensitivity, status, protocol)


@dataclass(frozen=True)
class AutomationThreshold:
    min_samples_per_category: int
    max_confidence_interval_width: float
    min_important_difference: float

    def __post_init__(self) -> None:
        if self.min_samples_per_category < 1:
            raise ValueError("min_samples_per_category must be positive")
        if self.max_confidence_interval_width <= 0 or self.min_important_difference < 0:
            raise ValueError("thresholds must be non-negative and width must be positive")


def evaluate_phase_transition(
    sample_counts: Mapping[str, int],
    confidence_interval_width: float,
    effect: float,
    threshold: AutomationThreshold,
) -> dict[str, Any]:
    """Gate automation transitions on configured sample and interval minima."""
    under_sampled = [category for category, count in sample_counts.items() if count < threshold.min_samples_per_category]
    width_ok = confidence_interval_width <= threshold.max_confidence_interval_width
    effect_ok = abs(effect) >= threshold.min_important_difference
    eligible = not under_sampled and width_ok and effect_ok
    return {
        "status": "eligible" if eligible else "blocked",
        "under_sampled_categories": under_sampled,
        "confidence_interval_width": confidence_interval_width,
        "width_ok": width_ok,
        "effect": effect,
        "effect_ok": effect_ok,
        "threshold": {
            "min_samples_per_category": threshold.min_samples_per_category,
            "max_confidence_interval_width": threshold.max_confidence_interval_width,
            "min_important_difference": threshold.min_important_difference,
        },
    }


class ArtifactFieldClass(StrEnum):
    MACHINE = "machine"
    OPERATOR_FACING = "operator_facing"
    CASE_ORIGINAL = "case_original"


@dataclass(frozen=True)
class ArtifactLanguagePolicy:
    machine_language: str = "en"

    def classify(self, field_name: str) -> ArtifactFieldClass:
        if field_name in {"case_text", "case_prompt", "evaluation_case"}:
            return ArtifactFieldClass.CASE_ORIGINAL
        if field_name in {"human_guidance", "report", "rationale", "escalation"}:
            return ArtifactFieldClass.OPERATOR_FACING
        return ArtifactFieldClass.MACHINE

    def validate_machine_language(self, record_language: str, fields: Mapping[str, str]) -> list[str]:
        """Return violations; free text outside machine fields is not rejected."""
        violations: list[str] = []
        for field_name, language in fields.items():
            if self.classify(field_name) == ArtifactFieldClass.MACHINE and language != self.machine_language:
                violations.append(f"{field_name}: expected {self.machine_language}, got {language}")
        return violations
