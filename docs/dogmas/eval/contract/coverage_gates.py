"""Coverage gates for evaluation claims.

A claim is a statement that this evaluator is willing to defend at a
declared scope (``case``, ``dimension``, ``candidate``, ``category``,
``model``, ``global``). The gate logic in this module decides whether a
claim may be emitted, must be downgraded to preliminary, or must be
blocked entirely.

The gates combine:

* repetition coverage per dimension,
* provenance status (``verified``, ``provisional``, ``limited``,
  ``unverified``),
* category-level coverage (how many distinct dimensions are sampled),
* contamination exclusions,
* legacy-limited provenance for any result in the claim.

High-confidence scopes (``category``, ``model``, ``global``) cannot be
emitted when any of the above is insufficient. Lower scopes
(``case``, ``dimension``, ``candidate``) may still be reported but are
explicitly downgraded to preliminary whenever the gate is tight.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Any, Iterable, Mapping, Sequence


class ClaimScope(StrEnum):
    CASE = "case"
    DIMENSION = "dimension"
    CANDIDATE = "candidate"
    CATEGORY = "category"
    MODEL = "model"
    GLOBAL = "global"


class GateVerdict(StrEnum):
    PASS = "pass"
    PRELIMINARY = "preliminary"
    BLOCK = "block"


class GateReason(StrEnum):
    SUFFICIENT = "sufficient"
    REPETITIONS_UNDER = "repetitions_under"
    PROVENANCE_INSUFFICIENT = "provenance_insufficient"
    CATEGORY_COVERAGE_UNDER = "category_coverage_under"
    CONTAMINATED_RESULTS = "contaminated_results"
    LEGACY_LIMITED = "legacy_limited"
    HIGH_CONFIDENCE_SCOPE = "high_confidence_scope_unjustified"


@dataclass(frozen=True)
class CoverageConfig:
    min_repetitions: int = 2
    min_categories: int = 2
    allowed_provenance: tuple[str, ...] = ("verified", "provisional", "limited")
    block_on_contamination: bool = True
    block_on_legacy: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_repetitions": self.min_repetitions,
            "min_categories": self.min_categories,
            "allowed_provenance": list(self.allowed_provenance),
            "block_on_contamination": self.block_on_contamination,
            "block_on_legacy": self.block_on_legacy,
        }


@dataclass(frozen=True)
class GateOutcome:
    scope: ClaimScope
    verdict: GateVerdict
    reasons: tuple[GateReason, ...]
    supporting_cases: tuple[str, ...]
    supporting_categories: tuple[str, ...]
    repetitions_observed: int

    @property
    def blocked(self) -> bool:
        return self.verdict == GateVerdict.BLOCK

    @property
    def downgraded(self) -> bool:
        return self.verdict != GateVerdict.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope.value,
            "verdict": self.verdict.value,
            "reasons": [r.value for r in self.reasons],
            "supporting_cases": list(self.supporting_cases),
            "supporting_categories": list(self.supporting_categories),
            "repetitions_observed": self.repetitions_observed,
            "blocked": self.blocked,
            "downgraded": self.downgraded,
        }


def evaluate_gate(
    scope: ClaimScope | str,
    results: Sequence[Mapping[str, Any]],
    *,
    config: CoverageConfig | None = None,
) -> GateOutcome:
    """Evaluate whether a claim at ``scope`` is supported by ``results``.

    ``results`` is a sequence of evaluation records (any mapping that
    exposes ``case_id``, ``provenance_status``, ``dimension``,
    ``category``, ``classification``, ``repetition_id``, and
    ``evidence_mode``). Records with ``evidence_mode == "legacy_limited"``
    or ``provenance_status == "unverified"`` are excluded from
    supporting the gate; they contribute to reporting but not to the
    verdict.
    """
    cfg = config or CoverageConfig()
    scope_enum = ClaimScope(scope) if not isinstance(scope, ClaimScope) else scope
    is_global = scope_enum == ClaimScope.GLOBAL
    requires_coverage = scope_enum in {ClaimScope.CATEGORY, ClaimScope.MODEL, ClaimScope.GLOBAL}

    supporting: list[Mapping[str, Any]] = []
    contaminated: list[str] = []
    legacy_limited: list[str] = []

    for record in results:
        if record.get("contaminated"):
            contaminated.append(str(record.get("case_id", "unknown")))
            continue
        if record.get("evidence_mode") == "legacy_limited" or record.get("provenance_status") == "unverified":
            legacy_limited.append(str(record.get("case_id", "unknown")))
            continue
        supporting.append(record)

    supporting_cases = tuple(sorted({str(r.get("case_id", "unknown")) for r in supporting}))
    categories = tuple(sorted({str(r.get("category", "unknown")) for r in supporting if r.get("category")}))
    provenance = {str(r.get("provenance_status", "unknown")) for r in supporting}

    pair_count = sum(int(r.get("repetition_count") or 1) for r in supporting)

    reasons: list[GateReason] = []
    verdict = GateVerdict.PASS

    required_repetitions = cfg.min_repetitions if is_global else 1
    if pair_count < required_repetitions:
        reasons.append(GateReason.REPETITIONS_UNDER)
        verdict = GateVerdict.BLOCK if is_global else GateVerdict.PRELIMINARY

    if not provenance.issubset(set(cfg.allowed_provenance)):
        reasons.append(GateReason.PROVENANCE_INSUFFICIENT)
        verdict = GateVerdict.BLOCK if is_global else GateVerdict.PRELIMINARY

    if requires_coverage and len(categories) < cfg.min_categories:
        reasons.append(GateReason.CATEGORY_COVERAGE_UNDER)
        verdict = GateVerdict.BLOCK if is_global else GateVerdict.PRELIMINARY

    if cfg.block_on_contamination and contaminated:
        reasons.append(GateReason.CONTAMINATED_RESULTS)
        verdict = GateVerdict.BLOCK

    if cfg.block_on_legacy and legacy_limited:
        reasons.append(GateReason.LEGACY_LIMITED)
        verdict = GateVerdict.BLOCK

    if any(r.get("provenance_status") in {"provisional", "limited"} for r in supporting):
        reasons.append(GateReason.PROVENANCE_INSUFFICIENT)
        if is_global:
            verdict = GateVerdict.BLOCK
        elif verdict == GateVerdict.PASS:
            verdict = GateVerdict.PRELIMINARY

    if is_global and verdict == GateVerdict.BLOCK and GateReason.HIGH_CONFIDENCE_SCOPE not in reasons:
        reasons.append(GateReason.HIGH_CONFIDENCE_SCOPE)

    if verdict == GateVerdict.PASS and reasons:
        verdict = GateVerdict.PRELIMINARY

    return GateOutcome(
        scope=scope_enum,
        verdict=verdict,
        reasons=tuple(reasons),
        supporting_cases=supporting_cases,
        supporting_categories=categories,
        repetitions_observed=pair_count,
    )


def filter_supporting(results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return only records that may contribute to a claim.

    The filter is conservative: contaminated, legacy-limited, or
    unverified records are excluded. The function never mutates its input.
    """
    kept: list[dict[str, Any]] = []
    for record in results:
        if record.get("contaminated"):
            continue
        if record.get("evidence_mode") == "legacy_limited":
            continue
        if record.get("provenance_status") == "unverified":
            continue
        kept.append(dict(record))
    return kept


def emit_gate_blocked_claim(scope: ClaimScope | str) -> dict[str, Any]:
    """Return the descriptor emitted in place of a blocked claim.

    The descriptor never carries the claim's conclusion. It tells the
    reader that the claim was blocked and lists the categories that
    would have been required.
    """
    return {
        "scope": ClaimScope(scope).value if not isinstance(scope, ClaimScope) else scope.value,
        "claim": None,
        "verdict": GateVerdict.BLOCK.value,
        "note": "claim suppressed: coverage gate blocked emission",
    }


def gate_to_json(outcome: GateOutcome) -> str:
    return json.dumps(outcome.to_dict(), sort_keys=True, ensure_ascii=False)