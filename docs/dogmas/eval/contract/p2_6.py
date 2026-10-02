"""P2.6 contracts for challenge objectives and outcome attribution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
from typing import Any, Iterable, Mapping


class ChallengeObjective(StrEnum):
    CORRECTIVE = "corrective"
    ADVERSARIAL = "adversarial"
    MIXED = "mixed"


class ChallengeAuthority(StrEnum):
    HUMAN = "human"
    RULE = "rule"
    JUDGE = "judge"
    HEURISTIC = "heuristic"
    UNVERIFIED = "unverified"


class OutcomeDimension(StrEnum):
    CORRECTION = "correction"
    STABILITY = "stability"


class AttributionStatus(StrEnum):
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    PROVISIONAL = "provisional"
    UNVERIFIED = "unverified"


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChallengeProvenance:
    """Origin and delivery metadata for a challenge."""

    authority: ChallengeAuthority
    generator_identity: str
    generator_version: str
    generated_model: str
    generated_sampling: Mapping[str, Any]
    target_turn: str
    content_hash: str
    delivered_content_hash: str | None = None
    evidence_hashes: tuple[str, ...] = ()
    human_edited: bool = False
    shared_model_family: bool = False

    def __post_init__(self) -> None:
        if not self.generator_identity or not self.generator_version:
            raise ValueError("generator_identity and generator_version are required")
        if not self.target_turn:
            raise ValueError("target_turn is required")
        if len(self.content_hash) != 64:
            raise ValueError("content_hash must be a SHA-256 hash")
        if self.delivered_content_hash is not None and len(self.delivered_content_hash) != 64:
            raise ValueError("delivered_content_hash must be a SHA-256 hash")

    @property
    def content_changed_in_delivery(self) -> bool:
        return self.delivered_content_hash is not None and self.delivered_content_hash != self.content_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority": self.authority.value,
            "generator_identity": self.generator_identity,
            "generator_version": self.generator_version,
            "generated_model": self.generated_model,
            "generated_sampling": dict(self.generated_sampling),
            "target_turn": self.target_turn,
            "content_hash": self.content_hash,
            "delivered_content_hash": self.delivered_content_hash,
            "evidence_hashes": list(self.evidence_hashes),
            "human_edited": self.human_edited,
            "shared_model_family": self.shared_model_family,
            "content_changed_in_delivery": self.content_changed_in_delivery,
        }


@dataclass(frozen=True)
class Challenge:
    """A challenge with an explicit objective and provenance."""

    objective: ChallengeObjective
    provenance: ChallengeProvenance

    def __post_init__(self) -> None:
        if self.objective == ChallengeObjective.CORRECTIVE and self.provenance.authority == ChallengeAuthority.UNVERIFIED:
            raise ValueError("unverified challenge cannot be treated as corrective")

    @property
    def objective_supports_correction(self) -> bool:
        return self.objective in {ChallengeObjective.CORRECTIVE, ChallengeObjective.MIXED}

    @property
    def objective_supports_stability(self) -> bool:
        return self.objective in {ChallengeObjective.ADVERSARIAL, ChallengeObjective.MIXED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective.value,
            **self.provenance.to_dict(),
        }


def validate_challenge(challenge: Challenge) -> dict[str, Any]:
    """Validate provenance and report flags that limit interpretation."""
    warnings: list[str] = []
    if challenge.provenance.authority == ChallengeAuthority.UNVERIFIED:
        warnings.append("challenge authority is unverified")
    if challenge.provenance.shared_model_family:
        warnings.append("challenge shares model family with evaluated agent")
    if challenge.provenance.content_changed_in_delivery and not challenge.provenance.human_edited:
        warnings.append("delivered challenge hash differs without human edit marker")
    return {
        "valid": not warnings,
        "warnings": warnings,
        "objective": challenge.objective.value,
        "authority": challenge.provenance.authority.value,
    }


def attribute_challenge_outcome(
    challenge: Challenge,
    *,
    dimension: OutcomeDimension,
    outcome: str,
    evidence_linked: bool,
    human_intervention: bool = False,
) -> dict[str, Any]:
    """Attribute a result only to dimensions supported by the objective.

    A corrective challenge can support correction evidence, an adversarial
    challenge can support stability evidence, and a mixed challenge can support
    both. Missing evidence or human intervention keeps the attribution
    provisional rather than silently treating it as an agent-only outcome.
    """
    supported = (
        challenge.objective_supports_correction
        if dimension == OutcomeDimension.CORRECTION
        else challenge.objective_supports_stability
    )
    if not supported:
        status = AttributionStatus.NOT_SUPPORTED
    elif not evidence_linked:
        status = AttributionStatus.UNVERIFIED
    elif human_intervention:
        status = AttributionStatus.PROVISIONAL
    else:
        status = AttributionStatus.SUPPORTED
    return {
        "objective": challenge.objective.value,
        "dimension": dimension.value,
        "outcome": outcome,
        "status": status.value,
        "evidence_linked": evidence_linked,
        "human_intervention": human_intervention,
        "challenge_hash": challenge.provenance.content_hash,
        "challenge_authority": challenge.provenance.authority.value,
    }


def validate_objective_consistency(
    challenge: Challenge,
    outcomes: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Find outcome records that contradict the declared challenge objective."""
    mismatches: list[dict[str, Any]] = []
    for outcome in outcomes:
        dimension = outcome.get("dimension")
        if dimension == OutcomeDimension.CORRECTION.value and not challenge.objective_supports_correction:
            mismatches.append(dict(outcome))
        elif dimension == OutcomeDimension.STABILITY.value and not challenge.objective_supports_stability:
            mismatches.append(dict(outcome))
    return {
        "consistent": not mismatches,
        "objective": challenge.objective.value,
        "mismatches": mismatches,
    }
