"""P2.1 contracts for judge controls, paired statistics, and evidence retention.

The helpers in this module are deliberately dependency-light: evaluation reports
must remain reproducible when optional scientific packages are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import math
import random
from typing import Any, Iterable, Sequence

try:
    from .evidence_custody import EvidenceCustody, resolve_custody
except ImportError:  # direct test/module execution
    from evidence_custody import EvidenceCustody, resolve_custody


@dataclass(frozen=True)
class JudgeMetadata:
    """Provenance and bias controls for a classification judge."""

    judge_id: str
    model_family_relation: bool | None = None
    agreement_validated: bool = False
    condition_blinded: bool = False
    comparison_order: str = "A_then_B"

    def __post_init__(self) -> None:
        if not self.judge_id:
            raise ValueError("judge_id is required")
        if self.comparison_order not in {"A_then_B", "B_then_A"}:
            raise ValueError("comparison_order must be A_then_B or B_then_A")

    @property
    def classification_status(self) -> str:
        return "validated" if self.agreement_validated else "provisional"

    def to_dict(self) -> dict[str, Any]:
        return {
            "judge_id": self.judge_id,
            "model_family_relation": self.model_family_relation,
            "agreement_validated": self.agreement_validated,
            "condition_blinded": self.condition_blinded,
            "comparison_order": self.comparison_order,
            "classification_status": self.classification_status,
        }


def comparison_order(pair_key: str, *, swap: bool = False) -> str:
    """Choose a reproducible comparison order and optionally swap it."""
    digest = hashlib.sha256(pair_key.encode("utf-8")).digest()
    first = "A_then_B" if digest[0] % 2 == 0 else "B_then_A"
    if swap:
        return "B_then_A" if first == "A_then_B" else "A_then_B"
    return first


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


def paired_mcnemar(
    condition_a: Sequence[bool],
    condition_b: Sequence[bool],
    *,
    confidence: float = 0.95,
    bootstrap_runs: int = 2000,
    seed: int = 0,
) -> dict[str, Any]:
    """Compare paired binary outcomes with exact McNemar and a paired CI.

    ``discordant_a_wins`` counts A=True/B=False and ``discordant_b_wins``
    counts A=False/B=True. The confidence interval is a reproducible paired
    bootstrap interval for the per-case pass-rate difference A minus B.
    """
    if len(condition_a) != len(condition_b):
        raise ValueError("paired conditions must have equal length")
    if not condition_a:
        raise ValueError("at least one paired case is required")
    pairs = list(zip(condition_a, condition_b))
    a_wins = sum(a and not b for a, b in pairs)
    b_wins = sum((not a) and b for a, b in pairs)
    differences = [int(a) - int(b) for a, b in pairs]
    delta = sum(differences) / len(differences)
    rng = random.Random(seed)
    bootstraps: list[float] = []
    for _ in range(max(1, bootstrap_runs)):
        sample = [differences[rng.randrange(len(differences))] for _ in differences]
        bootstraps.append(sum(sample) / len(sample))
    alpha = (1.0 - confidence) / 2.0
    return {
        "method": "mcnemar_exact_with_paired_bootstrap_ci",
        "n": len(pairs),
        "discordant_a_wins": a_wins,
        "discordant_b_wins": b_wins,
        "concordant": len(pairs) - a_wins - b_wins,
        "delta_a_minus_b": delta,
        "confidence": confidence,
        "confidence_interval": [_percentile(bootstraps, alpha), _percentile(bootstraps, 1.0 - alpha)],
        "p_value": _binomial_two_sided_p(a_wins, a_wins + b_wins),
    }


def resolve_evidence_references(
    reference_hashes: Iterable[str],
    custody: EvidenceCustody,
    *,
    base_dir: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve cited hashes and report missing or mismatched evidence."""
    requested = list(dict.fromkeys(reference_hashes))
    resolution = resolve_custody(custody, base_dir=base_dir, now=now)
    available = set(resolution["resolved"].values())
    verified = [value for value in requested if value in available]
    missing = [value for value in requested if value not in available]
    return {
        "custody_id": custody.custody_id,
        "custody_state": resolution["state"],
        "requested_hashes": requested,
        "verified_hashes": verified,
        "unresolved_hashes": missing,
        "verified": bool(requested) and not missing and resolution["state"] != "CORRUPTED",
        "resolution": resolution,
    }


@dataclass(frozen=True)
class RetentionPolicy:
    """Policy for literal response storage and hash-only fallback."""

    default_mode: str = "hash_only"
    require_expiry_for_literal: bool = True

    def __post_init__(self) -> None:
        if self.default_mode not in {"hash_only", "stored_literal"}:
            raise ValueError("default_mode must be hash_only or stored_literal")


def apply_retention_policy(
    result: dict[str, Any],
    custody: EvidenceCustody,
    *,
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply custody resolution and retention semantics without mutating result."""
    policy = policy or RetentionPolicy()
    updated = dict(result)
    resolution = resolve_custody(custody, now=now)
    mode = resolution["evidence_mode"]
    if policy.default_mode == "hash_only" and mode == "literal" and policy.require_expiry_for_literal:
        mode = "hash_only"
    updated["evidence_mode"] = mode
    updated["provenance_status"] = resolution["provenance_status"]
    updated["evaluation_validity"] = "invalidated" if resolution["state"] == "CORRUPTED" else (
        "limited" if mode == "hash_only" else updated.get("evaluation_validity", "valid")
    )
    updated["evidence"] = dict(updated.get("evidence", {}))
    updated["evidence"].update({"custody_id": custody.custody_id, "custody_state": resolution["state"]})
    if resolution["state"] == "CORRUPTED":
        updated["invalidation_reason"] = "evidence custody is CORRUPTED"
    elif resolution["literal_expired"]:
        updated["invalidation_reason"] = "stored literal expired; hash-only evidence retained"
    return updated
