"""Claim-emission profiles (tasks 9.5 and 9.6).

A profile decides which claim scopes may be emitted and with what
authority:

- ``vertical_slice``: preliminary by default, only ``candidate`` and
  ``dimension`` scopes allowed, no promotion authority. This is the
  first increment — every claim is preliminary until a ``full_suite``
  run validates it.
- ``full_suite``: every scope allowed, claims pass with promotion
  authority when the coverage gate permits.

Profiles never change Layer A enforcement; they only restrict what a
report may assert about the evidence the contract collected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet

from .coverage_gates import ClaimScope

_PROFILES: dict[str, "EvaluationProfile"] = {}


@dataclass(frozen=True)
class EvaluationProfile:
    """A claim-emission profile."""

    profile_id: str
    allowed_scopes: FrozenSet[ClaimScope]
    promotion_authority: bool
    preliminary_by_default: bool
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id is required")
        if not self.allowed_scopes:
            raise ValueError("a profile must allow at least one claim scope")


def vertical_slice_profile() -> EvaluationProfile:
    """The vertical-slice profile: candidate and dimension, preliminary only."""
    profile = EvaluationProfile(
        profile_id="vertical_slice@v1",
        allowed_scopes=frozenset({ClaimScope.CANDIDATE, ClaimScope.DIMENSION}),
        promotion_authority=False,
        preliminary_by_default=True,
        notes="First-increment profile; every emitted claim is preliminary.",
    )
    _PROFILES[profile.profile_id] = profile
    return profile


def full_suite_profile() -> EvaluationProfile:
    """The full-suite profile: every scope, with promotion authority."""
    profile = EvaluationProfile(
        profile_id="full_suite@v1",
        allowed_scopes=frozenset(ClaimScope),
        promotion_authority=True,
        preliminary_by_default=False,
        notes="Full-suite profile; passes every scope when coverage gates permit.",
    )
    _PROFILES[profile.profile_id] = profile
    return profile


def get_profile(profile_id: str) -> EvaluationProfile:
    if profile_id not in _PROFILES:
        raise KeyError(f"unknown profile: {profile_id}; available: {sorted(_PROFILES)}")
    return _PROFILES[profile_id]


def restrict_claim(profile: EvaluationProfile, scope: ClaimScope | str) -> dict[str, Any]:
    """Return a verdict for emitting a claim at ``scope`` under ``profile``.

    Verdict is one of:

    - ``block`` — scope is not allowed under the profile; the claim MUST
      not be emitted.
    - ``preliminary`` — scope is allowed but the profile has no
      promotion authority; the claim is emitted as preliminary.
    - ``pass`` — scope is allowed and the profile has promotion
      authority; the claim may be emitted at full confidence subject to
      coverage gates.
    """
    scope_enum = ClaimScope(scope) if not isinstance(scope, ClaimScope) else scope
    if scope_enum not in profile.allowed_scopes:
        return {
            "scope": scope_enum.value,
            "verdict": "block",
            "reason": (
                f"scope {scope_enum.value} is not allowed under profile "
                f"{profile.profile_id}; allowed scopes: "
                f"{sorted(s.value for s in profile.allowed_scopes)}"
            ),
        }
    if profile.preliminary_by_default:
        return {
            "scope": scope_enum.value,
            "verdict": "preliminary",
            "reason": f"profile {profile.profile_id} is preliminary by default",
        }
    return {
        "scope": scope_enum.value,
        "verdict": "pass",
        "reason": f"profile {profile.profile_id} grants promotion authority",
    }


vertical_slice_profile()
full_suite_profile()