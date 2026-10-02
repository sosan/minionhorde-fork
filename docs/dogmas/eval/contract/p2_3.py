"""P2.3 contracts for discriminating power, equivalence, claim validity, and multiplicity.

These helpers support statistical rigor without requiring external scientific
packages. They are dependency-light and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
from enum import StrEnum
from typing import Any, Iterable, Sequence


class Discrimination(StrEnum):
    CEILING = "ceiling"
    FLOOR = "floor"
    INERT = "inert"
    DISCRIMINATING = "discriminating"
    UNKNOWN = "unknown"


class ClaimStatus(StrEnum):
    DEFINITIVE = "definitive"
    PRELIMINARY = "preliminary"
    INCONCLUSIVE = "inconclusive"
    PENDING = "pending"
    INVALIDATED = "invalidated"


def _binomial_two_sided_p(successes: int, trials: int) -> float:
    if trials == 0:
        return 1.0
    probability = 0.5**trials
    observed = math.comb(trials, successes) * probability
    return min(1.0, sum(
        math.comb(trials, k) * probability
        for k in range(trials + 1)
        if math.comb(trials, k) * probability <= observed + 1e-15
    ))


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


@dataclass(frozen=True)
class DiscriminationResult:
    case_id: str
    discrimination: Discrimination
    pass_rate: float
    n: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "discrimination": self.discrimination.value,
            "pass_rate": self.pass_rate,
            "n": self.n,
            "reason": self.reason,
        }


def classify_discrimination(
    case_id: str,
    outcomes: Sequence[bool],
    *,
    ceiling_threshold: float = 0.95,
    floor_threshold: float = 0.05,
) -> DiscriminationResult:
    """Classify a case's discriminating power from its pass/fail history.

    ``ceiling``: almost always passes (no discrimination).
    ``floor``: almost always fails (no discrimination).
    ``inert``: mixed but not enough variance to be useful.
    ``discriminating``: shows meaningful variance across conditions.
    """
    if not outcomes:
        return DiscriminationResult(case_id, Discrimination.UNKNOWN, 0.0, 0, "no outcomes")
    n = len(outcomes)
    pass_rate = sum(outcomes) / n
    if pass_rate >= ceiling_threshold:
        return DiscriminationResult(case_id, Discrimination.CEILING, pass_rate, n, f"pass_rate {pass_rate:.2f} >= {ceiling_threshold}")
    if pass_rate <= floor_threshold:
        return DiscriminationResult(case_id, Discrimination.FLOOR, pass_rate, n, f"pass_rate {pass_rate:.2f} <= {floor_threshold}")
    if n < 3:
        return DiscriminationResult(case_id, Discrimination.INERT, pass_rate, n, f"insufficient repetitions n={n}")
    return DiscriminationResult(case_id, Discrimination.DISCRIMINATING, pass_rate, n, f"pass_rate {pass_rate:.2f} with n={n}")


@dataclass(frozen=True)
class TOSTResult:
    method: str
    n: int
    delta: float
    confidence: float
    margin: float
    confidence_interval: tuple[float, float]
    equivalence: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "n": self.n,
            "delta": self.delta,
            "confidence": self.confidence,
            "margin": self.margin,
            "confidence_interval": list(self.confidence_interval),
            "equivalence": self.equivalence,
            "reason": self.reason,
        }


def tost_equivalence(
    condition_a: Sequence[float],
    condition_b: Sequence[float],
    *,
    margin: float,
    confidence: float = 0.95,
    bootstrap_runs: int = 2000,
    seed: int = 0,
) -> TOSTResult:
    """Two-one-sided-tests (TOST) equivalence via paired bootstrap.

    Equivalence is declared when the confidence interval for the difference
    falls entirely within ``[-margin, +margin]``.
    """
    if len(condition_a) != len(condition_b):
        raise ValueError("paired conditions must have equal length")
    if not condition_a:
        raise ValueError("at least one paired observation is required")
    if margin <= 0:
        raise ValueError("margin must be positive")
    differences = [a - b for a, b in zip(condition_a, condition_b)]
    delta = sum(differences) / len(differences)
    import random
    rng = random.Random(seed)
    bootstraps: list[float] = []
    for _ in range(max(1, bootstrap_runs)):
        sample = [differences[rng.randrange(len(differences))] for _ in differences]
        bootstraps.append(sum(sample) / len(sample))
    alpha = (1.0 - confidence) / 2.0
    lower = _percentile(bootstraps, alpha)
    upper = _percentile(bootstraps, 1.0 - alpha)
    equivalence = -margin <= lower and upper <= margin
    if equivalence:
        reason = f"CI [{lower:.4f}, {upper:.4f}] within [-{margin}, +{margin}]"
    else:
        reason = f"CI [{lower:.4f}, {upper:.4f}] exceeds margin ±{margin}"
    return TOSTResult(
        method="tost_paired_bootstrap",
        n=len(differences),
        delta=delta,
        confidence=confidence,
        margin=margin,
        confidence_interval=(lower, upper),
        equivalence=equivalence,
        reason=reason,
    )


@dataclass
class ClaimValidity:
    claim_id: str
    created_at: str
    ttl_hours: float | None = None
    served_model: str = "unknown"
    criteria_version: str = "unknown"
    memory_version: str = "unknown"
    policy_version: str = "unknown"
    invalidated_by: str | None = None

    @property
    def status(self) -> ClaimStatus:
        if self.invalidated_by:
            return ClaimStatus.INVALIDATED
        if self.ttl_hours is None:
            return ClaimStatus.DEFINITIVE
        created = datetime.fromisoformat(self.created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now >= created + timedelta(hours=self.ttl_hours):
            return ClaimStatus.INVALIDATED
        return ClaimStatus.DEFINITIVE

    def invalidate(self, reason: str) -> None:
        self.invalidated_by = reason

    def revalidate_dependencies(
        self,
        *,
        served_model: str,
        criteria_version: str,
        memory_version: str,
        policy_version: str,
    ) -> bool:
        """Invalidate the claim when a provenance dependency changes."""
        current = {
            "served_model": served_model,
            "criteria_version": criteria_version,
            "memory_version": memory_version,
            "policy_version": policy_version,
        }
        recorded = {
            "served_model": self.served_model,
            "criteria_version": self.criteria_version,
            "memory_version": self.memory_version,
            "policy_version": self.policy_version,
        }
        changed = [key for key in recorded if recorded[key] != current[key]]
        if changed:
            self.invalidate("dependency changed: " + ", ".join(changed))
            return False
        return self.status != ClaimStatus.INVALIDATED
    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "ttl_hours": self.ttl_hours,
            "served_model": self.served_model,
            "criteria_version": self.criteria_version,
            "memory_version": self.memory_version,
            "policy_version": self.policy_version,
            "invalidated_by": self.invalidated_by,
        }


@dataclass(frozen=True)
class PreRegisteredInclusion:
    """Pre-registered case-inclusion rules for a contrast."""
    primary_contrast: str
    primary_dimension: str
    included_case_ids: tuple[str, ...]
    excluded_case_ids: tuple[str, ...] = ()
    exclusion_reason: str = ""

    def __post_init__(self) -> None:
        overlap = set(self.included_case_ids) & set(self.excluded_case_ids)
        if overlap:
            raise ValueError(f"cases in both included and excluded: {overlap}")

    def is_included(self, case_id: str) -> bool:
        return case_id in self.included_case_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_contrast": self.primary_contrast,
            "primary_dimension": self.primary_dimension,
            "included_case_ids": list(self.included_case_ids),
            "excluded_case_ids": list(self.excluded_case_ids),
            "exclusion_reason": self.exclusion_reason,
        }


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment for multiple comparisons."""
    if not p_values:
        return []
    n = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    for rank, (idx, p) in enumerate(indexed):
        adjusted[idx] = min(1.0, p * (n - rank))
    for rank in range(1, n):
        adjusted[rank] = max(adjusted[rank], adjusted[rank - 1])
    return adjusted


def apply_multiplicity(
    p_values: Sequence[float],
    *,
    primary_index: int | None = None,
    method: str = "holm",
) -> dict[str, Any]:
    """Apply multiplicity control and identify primary vs secondary claims."""
    if method != "holm":
        raise ValueError("only holm method is supported")
    adjusted = holm_adjust(p_values)
    if primary_index is not None and primary_index < len(adjusted):
        primary_p = adjusted[primary_index]
    else:
        primary_p = None
    return {
        "method": method,
        "raw_p_values": list(p_values),
        "adjusted_p_values": adjusted,
        "primary_index": primary_index,
        "primary_adjusted_p": primary_p,
        "significant_at_0.05": [i for i, p in enumerate(adjusted) if p < 0.05],
    }
