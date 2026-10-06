"""Tests for tasks 9.5 and 9.6 — claim profiles and scope restriction.

A ``vertical_slice`` profile is preliminary by default, allows only
``candidate`` and ``dimension`` scopes, and has no promotion authority.
A ``full_suite`` profile allows all scopes with promotion authority.
The ``restrict_claim`` function MUST return a verdict consistent with the
profile and the declared scope.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from contract.profiles import (
    EvaluationProfile,
    full_suite_profile,
    restrict_claim,
    vertical_slice_profile,
)
from contract.coverage_gates import ClaimScope


def test_vertical_slice_profile_allows_only_candidate_and_dimension() -> None:
    profile = vertical_slice_profile()
    assert profile.allowed_scopes == frozenset({ClaimScope.CANDIDATE, ClaimScope.DIMENSION})
    assert profile.preliminary_by_default is True
    assert profile.promotion_authority is False


def test_full_suite_profile_allows_every_scope_with_promotion() -> None:
    profile = full_suite_profile()
    assert profile.allowed_scopes == frozenset(ClaimScope)
    assert profile.promotion_authority is True
    assert profile.preliminary_by_default is False


def test_vertical_slice_blocks_global_scope() -> None:
    profile = vertical_slice_profile()
    decision = restrict_claim(profile, ClaimScope.GLOBAL)
    assert decision["verdict"] == "block"
    assert "vertical_slice" in decision["reason"]


def test_vertical_slice_emits_dimension_as_preliminary() -> None:
    profile = vertical_slice_profile()
    decision = restrict_claim(profile, ClaimScope.DIMENSION)
    assert decision["verdict"] == "preliminary"
    assert decision["scope"] == "dimension"


def test_vertical_slice_emits_candidate_as_preliminary() -> None:
    profile = vertical_slice_profile()
    decision = restrict_claim(profile, ClaimScope.CANDIDATE)
    assert decision["verdict"] == "preliminary"


def test_vertical_slice_blocks_case_category_and_model_scopes() -> None:
    profile = vertical_slice_profile()
    for scope in (ClaimScope.CASE, ClaimScope.CATEGORY, ClaimScope.MODEL):
        decision = restrict_claim(profile, scope)
        assert decision["verdict"] == "block", scope


def test_full_suite_passes_every_scope() -> None:
    profile = full_suite_profile()
    for scope in ClaimScope:
        decision = restrict_claim(profile, scope)
        assert decision["verdict"] == "pass", scope


def test_profiles_are_distinct() -> None:
    assert vertical_slice_profile().profile_id != full_suite_profile().profile_id
    assert vertical_slice_profile() != full_suite_profile()


def test_restrict_claim_accepts_string_scope() -> None:
    profile = vertical_slice_profile()
    decision = restrict_claim(profile, "dimension")
    assert decision["scope"] == "dimension"
    assert decision["verdict"] == "preliminary"