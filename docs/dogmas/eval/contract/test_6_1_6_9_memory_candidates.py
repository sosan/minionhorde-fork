"""Tests for tasks 6.1-6.5, 6.7-6.9 — versioned provisional memory candidates.

Contract source: specs/operational-learning/spec.md, "Memory candidates are
versioned and reversible":

* 6.1  candidate records carry status, provenance, episodes, transfer cases,
       counterexamples, scope, parent version, deprecation; auto-promotion to
       the active dogma is prohibited.
* 6.2  a provisional candidate is created only from the configured minimum of
       distinct sessions/cases sharing a mechanism, with no contaminated
       episode; it references the episodes and identifies required transfer
       and regression tests.
* 6.3  promotion requires transfer/regression passes plus human review and
       produces a new memory version while retaining the previous one.
* 6.4  a contradicting case deprecates or narrows the candidate, preserving
       history and never deleting evidence.
* 6.5  regression tests cover promotion refusal, rollback selection,
       deprecation, and normative-inflation prevention.
* 6.7  support contamination is detected by hash equality or declared
       semantic similarity.
* 6.8  the episode minimum is enforced and contaminated support rejects
       candidate creation.
* 6.9  promotion is rejected on contaminated support or open frontier
       dissent until episodes are replaced and dissent is routed to human
       review and closed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.memory_candidates import (
    CandidatePolicy,
    CandidateRecord,
    CandidateStatus,
    EpisodeRef,
    attempt_promotion,
    detect_support_contamination,
    mark_invalidated,
    propose_candidate,
    rollback_to,
)


def _episode(
    episode_id: str = "ep-1",
    session_id: str = "s1",
    case_id: str = "c1",
    case_hash: str | None = None,
    mechanism: str = "guard-clause-before-side-effect",
    contaminated: bool = False,
    similarity_declared: bool = False,
) -> EpisodeRef:
    if case_hash is None:
        case_hash = f"hash-{case_id}"
    return EpisodeRef(
        episode_id=episode_id,
        session_id=session_id,
        case_id=case_id,
        case_hash=case_hash,
        mechanism=mechanism,
        contaminated=contaminated,
        similarity_declared=similarity_declared,
    )


def _clean_episodes() -> list[EpisodeRef]:
    return [_episode("ep-1", "s1", "c1"), _episode("ep-2", "s2", "c2")]


# --- 6.1 candidate records ------------------------------------------------


def test_candidate_record_carries_versioned_fields() -> None:
    candidate = propose_candidate(
        _clean_episodes(),
        CandidatePolicy(),
        scope="dogmas/core:rule-construction",
        transfer_cases=("t1",),
    )
    assert isinstance(candidate, CandidateRecord)
    assert candidate.status == CandidateStatus.PROVISIONAL
    assert candidate.scope == "dogmas/core:rule-construction"
    assert candidate.parent_version is None
    assert candidate.version == "v1"
    assert [e.episode_id for e in candidate.episodes] == ["ep-1", "ep-2"]
    assert "t1" in candidate.transfer_cases
    assert candidate.counterexamples == ()
    assert candidate.deprecation is None


def test_auto_promotion_to_active_core_is_prohibited() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    decision = attempt_promotion(
        candidate,
        human_reviewed=False,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "human_review_required"


def test_auto_promotion_cannot_be_enabled_by_policy() -> None:
    policy = CandidatePolicy(min_episodes=2, auto_promotion_allowed=True)
    assert policy.auto_promotion_allowed is False


# --- 6.2 provisional candidate creation ----------------------------------


def test_candidate_created_only_from_minimum_episodes() -> None:
    decision = propose_candidate([_episode("ep-1", "s1", "c1")], CandidatePolicy(min_episodes=2), scope="s")
    assert decision["status"] == "rejected"
    assert decision["reason"] == "insufficient_episodes"


def test_candidate_requires_distinct_cases() -> None:
    same_case = [_episode("ep-1", "s1", "c1"), _episode("ep-2", "s2", "c1")]
    decision = propose_candidate(same_case, CandidatePolicy(min_episodes=2, require_distinct_cases=True), scope="s")
    assert decision["status"] == "rejected"
    assert decision["reason"] == "insufficient_distinct_cases"


def test_candidate_identifies_required_transfer_and_regression_tests() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    assert "transfer" in candidate.required_tests
    assert "regression" in candidate.required_tests


def test_provisional_candidate_never_writes_to_active_core() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    assert candidate.status == CandidateStatus.PROVISIONAL
    assert "promoted" not in candidate.status


# --- 6.3 promotion, versioning, rollback ----------------------------------


def test_promotion_creates_new_version_keeping_previous_for_rollback() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    promoted = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
    )
    assert promoted["status"] == "promoted"
    assert promoted["version"] == "v2"
    assert promoted["parent_version"] == "v1"
    assert rollback_to(promoted["record"]) is not None
    assert rollback_to(promoted["record"]).version == "v1"
    assert rollback_to(promoted["record"]).status == CandidateStatus.PROVISIONAL


def test_promotion_rejected_without_human_review() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    decision = attempt_promotion(
        candidate,
        human_reviewed=False,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "human_review_required"


def test_promotion_rejected_when_manifest_hash_missing() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    decision = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash=None,
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "manifest_hash_required"


def test_promotion_rejected_when_validation_fails() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    decision = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=False,
        regression_passed=True,
        manifest_hash="manifest-hash",
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "validation_failed"


# --- 6.4 deprecation / narrowing ------------------------------------------


def test_contradiction_deprecates_preserving_history_and_evidence() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    invalidated = mark_invalidated(
        candidate,
        reason="later case contradicts scope 's'",
        mode="deprecated",
    )
    assert invalidated.status == CandidateStatus.DEPRECATED
    assert invalidated.deprecation is not None
    assert [e.episode_id for e in invalidated.episodes] == ["ep-1", "ep-2"]
    assert rollback_to(invalidated) is not None


def test_contradiction_can_narrow_scope() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    narrowed = mark_invalidated(
        candidate,
        reason="scope narrowed to s-subset",
        mode="narrowed",
    )
    assert narrowed.status == CandidateStatus.NARROWED
    assert narrowed.deprecation == "scope narrowed to s-subset"


# --- 6.5 regression: refusal, rollback, inflation --------------------------

def test_promotion_refusal_regression_contaminated() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    decision = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
        open_dissents=(),
        evaluation_cases={"hash-c2"},
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "contaminated_support"


def test_rollback_restores_previous_version() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    promoted = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
    )
    assert rollback_to(promoted["record"]).status == CandidateStatus.PROVISIONAL


def test_deprecation_preserves_counterexamples_evidence() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    invalidated = mark_invalidated(candidate, reason="contradicted", mode="deprecated")
    assert invalidated.counterexamples == ()
    assert invalidated.episodes  # evidence retained


def test_normative_inflation_prevented_by_default() -> None:
    policy = CandidatePolicy()
    assert policy.auto_promotion_allowed is False


# --- 6.7 contamination checking -------------------------------------------

def test_contamination_detected_by_hash_equality() -> None:
    episodes = _clean_episodes()
    contaminated = detect_support_contamination(episodes, case_hashes={"hash-c2"})
    assert [e.episode_id for e in contaminated] == ["ep-2"]


def test_contamination_semantic_similarity_declared() -> None:
    episodes = [_episode("ep-1", "s1", "c1"), _episode("ep-2", "s2", "c2", similarity_declared=True)]
    contaminated = detect_support_contamination(episodes, case_hashes=set(), similarity_mode=True)
    assert [e.episode_id for e in contaminated] == ["ep-2"]


def test_exact_mode_ignores_thematic_overlap() -> None:
    episodes = [_episode("ep-1", "s1", "c1"), _episode("ep-2", "s2", "c2", similarity_declared=True)]
    contaminated = detect_support_contamination(episodes, case_hashes={"other"})
    assert contaminated == []


# --- 6.8 episode minimum and contaminated support ---------------------------

def test_candidate_creation_rejected_on_contaminated_support() -> None:
    decision = propose_candidate(
        [_episode("ep-1", "s1", "c1"), _episode("ep-2", "s2", "c2", contaminated=True)],
        CandidatePolicy(),
        scope="s",
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "contaminated_support"


def test_minimum_episodes_policy_default_is_at_least_two() -> None:
    assert CandidatePolicy().min_episodes >= 2


# --- 6.9 promotion gates on contamination and dissent ----------------------

def test_promotion_rejected_with_open_dissent() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    decision = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
        open_dissents=("frontier-dissent-1",),
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "open_dissent"
    assert "frontier-dissent-1" in decision["open_dissents"]


def test_promotion_allowed_after_dissent_closed_and_human_review() -> None:
    candidate = propose_candidate(_clean_episodes(), CandidatePolicy(), scope="s")
    assert isinstance(candidate, CandidateRecord)
    promoted = attempt_promotion(
        candidate,
        human_reviewed=True,
        transfer_passed=True,
        regression_passed=True,
        manifest_hash="manifest-hash",
        open_dissents=(),
    )
    assert promoted["status"] == "promoted"