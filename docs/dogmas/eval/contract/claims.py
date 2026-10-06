"""Degraded-scenario detection and claim restriction (task 3.5).

Four regression scenarios MUST downgrade any claim to preliminary:

* incomplete coverage — any supporting result is uncovered,
* mixed configurations — results ran under different served models or
  sampling (non-comparable),
* missing literal evidence — any supporting result has limited/unverified
  provenance or no literal evidence,
* model disagreement — verified results classify the same case
  differently (PASS vs FAIL).

Detection is deterministic and ordered so the most severe reason wins.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Iterable, Mapping

from .profiles import EvaluationProfile


class DegradedReason(StrEnum):
    INCOMPLETE_COVERAGE = "incomplete_coverage"
    MIXED_CONFIGURATIONS = "mixed_configurations"
    MISSING_LITERAL_EVIDENCE = "missing_literal_evidence"
    MODEL_DISAGREEMENT = "model_disagreement"


def _verified(results: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [r for r in results if r.get("provenance_status") == "verified"]


def detect_degradation(results: Iterable[Mapping[str, Any]]) -> DegradedReason | None:
    """Return the most severe degraded reason, or ``None`` when clean."""
    verified = _verified(results)
    judge_labels = {r.get("judge_classification") for r in verified if r.get("judge_classification") in ("PASS", "FAIL")}
    if len(judge_labels) >= 2:
        return DegradedReason.MODEL_DISAGREEMENT

    if any(r.get("provenance_status") != "verified" for r in results):
        return DegradedReason.MISSING_LITERAL_EVIDENCE

    comparabilities = {r.get("comparability") for r in results if r.get("comparability") in ("comparable", "non_comparable")}
    if len(comparabilities) >= 2:
        return DegradedReason.MIXED_CONFIGURATIONS

    if any(r.get("coverage_status") != "covered" for r in results):
        return DegradedReason.INCOMPLETE_COVERAGE

    return None


def restrict_claim_for_degraded(
    results: Iterable[Mapping[str, Any]],
    profile: EvaluationProfile,
    *,
    scope: str = "candidate",
) -> dict[str, Any]:
    """Restrict a claim under ``profile`` given the degraded scenario.

    Returns ``{"scope", "verdict", "reason"}``. Any degraded scenario
    downgrades the verdict to ``preliminary``; a clean batch lets the
    profile's own authority decide.
    """
    reason = detect_degradation(results)
    if reason is not None:
        return {
            "scope": scope,
            "verdict": "preliminary",
            "reason": reason,
            "downgraded_by": reason.value,
        }
    base = _profile_verdict(profile, scope)
    base["reason"] = None
    return base


def _profile_verdict(profile: EvaluationProfile, scope: str) -> dict[str, Any]:
    from .profiles import restrict_claim

    return restrict_claim(profile, scope)
