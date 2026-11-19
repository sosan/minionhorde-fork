"""Regression tests for the SRP split (C2): E1 universal in CORE, E2-E12 in the
evaluation profile. Guards against stale references and accidental re-merge.
"""
from __future__ import annotations

import pathlib

REPO_ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / ".git").exists())
CORE = (REPO_ROOT / ".claude/rules/DOGMAS-CORE.md").read_text(encoding="utf-8")
PROFILE = (REPO_ROOT / ".claude/rules/EVALUATION-PROFILE.md").read_text(encoding="utf-8")
SKILL = (REPO_ROOT / ".claude/skills/evaluation-contracts/SKILL.md").read_text(encoding="utf-8")


def test_core_keeps_universal_e1_boundary():
    assert "LAYER AUTHORITY (E1)" in CORE


def test_core_has_no_e2_e12_body():
    for i in range(2, 13):
        assert f"E{i} —" not in CORE, f"CORE must not carry E{i}"


def test_profile_has_all_e2_e12_once():
    for i in range(2, 13):
        assert PROFILE.count(f"**E{i} —") == 1, f"profile must define E{i} exactly once"


def test_core_points_to_profile():
    assert "EVALUATION-PROFILE.md" in CORE


def test_skill_requires_profile():
    assert "EVALUATION-PROFILE.md" in SKILL


def test_core_frozen_numbering_and_blocks_intact():
    for marker in (
        "SECURITY (does not suspend)",
        "OPERATION (suspends)",
        "FORMAT (suspends)",
        "STRUCTURE BLOCK (not suspended",
        "NEW INVARIANTS",
    ):
        assert marker in CORE