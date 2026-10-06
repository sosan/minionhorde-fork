"""Versioned provisional memory candidates (tasks 6.1-6.5, 6.7-6.9).

A memory candidate is the staging representation of a future dogma
amendment: it has a status, scope, supporting episodes, transfer cases,
counterexamples, parent version, and deprecation history. Candidates are
proposed from the configured minimum number of independently supported
episodes and are promoted only after a human review gate and validated
transfer and regression checks; auto-promotion to the active core is
prohibited.

Contract source: specs/operational-learning/spec.md,
"Memory candidates are versioned and reversible".
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Iterable, Sequence


class CandidateStatus(StrEnum):
    PROVISIONAL = "provisional"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    NARROWED = "narrowed"


@dataclass(frozen=True)
class EpisodeRef:
    """A supporting episode for a memory candidate."""

    episode_id: str
    session_id: str
    case_id: str
    case_hash: str
    mechanism: str
    contaminated: bool = False
    similarity_declared: bool = False


@dataclass(frozen=True)
class CandidatePolicy:
    """Configuration gates for proposing and promoting memory candidates."""

    min_episodes: int = 2
    require_distinct_cases: bool = True
    manifest_hash_required: bool = True
    auto_promotion_allowed: bool = False
    provenance_label: str = "provisional"

    def __post_init__(self) -> None:
        if self.min_episodes < 2:
            raise ValueError("min_episodes must be at least 2")
        if self.auto_promotion_allowed:
            object.__setattr__(self, "auto_promotion_allowed", False)


@dataclass(frozen=True)
class CandidateRecord:
    """A versioned memory candidate with full history."""

    candidate_id: str
    status: CandidateStatus
    scope: str
    version: str
    episodes: tuple[EpisodeRef, ...]
    provenance: str
    transfer_cases: tuple[str, ...] = ()
    counterexamples: tuple[str, ...] = ()
    parent_version: str | None = None
    required_tests: tuple[str, ...] = ()
    deprecation: str | None = None
    promotion_evidence: dict[str, Any] | None = None
    history: tuple["CandidateRecord", ...] = field(default_factory=tuple)


def _next_version(previous: str) -> str:
    if previous.startswith("v") and previous[1:].isdigit():
        return f"v{int(previous[1:]) + 1}"
    return f"{previous}+1"


def _eligibility_problems(episodes: Sequence[EpisodeRef], policy: CandidatePolicy) -> list[str]:
    problems: list[str] = []
    if len(episodes) < policy.min_episodes:
        problems.append("insufficient_episodes")
    if any(episode.contaminated for episode in episodes):
        problems.append("contaminated_support")
    if policy.require_distinct_cases:
        cases = {episode.case_id for episode in episodes}
        if len(cases) < policy.min_episodes:
            problems.append("insufficient_distinct_cases")
    return problems


def propose_candidate(
    episodes: Sequence[EpisodeRef],
    policy: CandidatePolicy,
    *,
    scope: str,
    candidate_id: str | None = None,
    transfer_cases: Sequence[str] = (),
) -> CandidateRecord | dict[str, Any]:
    """Propose a provisional candidate from supporting episodes.

    Returns a ``CandidateRecord`` when eligible; otherwise a rejection
    dict with ``status="rejected"`` and a single reason (the most
    specific problem wins: contaminated_support > insufficient_distinct_cases
    > insufficient_episodes).
    """
    problems = _eligibility_problems(episodes, policy)
    if problems:
        return {"status": "rejected", "reason": problems[0], "problems": problems}
    candidate_id = candidate_id or f"cand-{episodes[0].mechanism}"
    return CandidateRecord(
        candidate_id=candidate_id,
        status=CandidateStatus.PROVISIONAL,
        scope=scope,
        version="v1",
        episodes=tuple(episodes),
        provenance=policy.provenance_label,
        transfer_cases=tuple(transfer_cases),
        required_tests=("transfer", "regression"),
    )


def detect_support_contamination(
    episodes: Iterable[EpisodeRef],
    *,
    case_hashes: set[str] | None = None,
    similarity_mode: bool = False,
) -> list[EpisodeRef]:
    """Find episodes contaminated with the supporting evaluation cases.

    Exact-mode (default) matches by case_hash equality; similarity-mode
    additionally flags episodes whose supporting pipeline declared
    semantic overlap.
    """
    case_hashes = case_hashes or set()
    contaminated: list[EpisodeRef] = []
    for episode in episodes:
        if episode.contaminated:
            contaminated.append(episode)
            continue
        if episode.case_hash in case_hashes:
            contaminated.append(episode)
            continue
        if similarity_mode and episode.similarity_declared:
            contaminated.append(episode)
    return contaminated


def _has_contaminated_support(candidate: CandidateRecord) -> bool:
    return any(episode.contaminated for episode in candidate.episodes)


def attempt_promotion(
    candidate: CandidateRecord,
    *,
    human_reviewed: bool,
    transfer_passed: bool,
    regression_passed: bool,
    manifest_hash: str | None,
    open_dissents: Sequence[str] = (),
    evaluation_cases: set[str] | None = None,
    similarity_mode: bool = False,
) -> dict[str, Any]:
    """Promote a candidate to a new memory version, or reject it.

    Rejects when: human review is missing (6.1/6.5 normative-inflation
    prevention), any supporting episode is contaminated (6.7/6.9 —
    statically flagged, or detected live against the evaluation cases),
    a frontier dissent is open (6.9), the regression manifest hash is
    absent (5.12 unverifiable), or transfer/regression did not pass
    (6.3 validation).
    """
    if not human_reviewed:
        return {"status": "rejected", "reason": "human_review_required"}
    if _has_contaminated_support(candidate):
        return {"status": "rejected", "reason": "contaminated_support"}
    if detect_support_contamination(
        candidate.episodes,
        case_hashes=evaluation_cases,
        similarity_mode=similarity_mode,
    ):
        return {"status": "rejected", "reason": "contaminated_support"}
    if open_dissents:
        return {"status": "rejected", "reason": "open_dissent", "open_dissents": list(open_dissents)}
    if manifest_hash is None:
        return {"status": "rejected", "reason": "manifest_hash_required"}
    if not (transfer_passed and regression_passed):
        return {"status": "rejected", "reason": "validation_failed"}

    promoted_version = _next_version(candidate.version)
    promoted = CandidateRecord(
        candidate_id=candidate.candidate_id,
        status=CandidateStatus.PROMOTED,
        scope=candidate.scope,
        version=promoted_version,
        episodes=candidate.episodes,
        provenance=candidate.provenance,
        transfer_cases=candidate.transfer_cases,
        counterexamples=candidate.counterexamples,
        parent_version=candidate.version,
        required_tests=candidate.required_tests,
        promotion_evidence={
            "transfer_passed": transfer_passed,
            "regression_passed": regression_passed,
            "manifest_hash": manifest_hash,
            "open_dissents": list(open_dissents),
        },
        history=candidate.history + (candidate,),
    )
    return {
        "status": "promoted",
        "record": promoted,
        "version": promoted.version,
        "parent_version": promoted.parent_version,
    }


def mark_invalidated(
    candidate: CandidateRecord,
    *,
    reason: str,
    mode: str = "deprecated",
) -> CandidateRecord:
    """Mark a candidate as deprecated or narrowed, preserving evidence.

    Episodes, counterexamples, and history are all preserved: the
    spec requires that the contradicting case never deletes the evidence
    the candidate rested on.
    """
    if mode not in ("deprecated", "narrowed"):
        raise ValueError(f"invalid mode: {mode!r}")
    new_status = CandidateStatus.DEPRECATED if mode == "deprecated" else CandidateStatus.NARROWED
    return replace(
        candidate,
        status=new_status,
        version=_next_version(candidate.version),
        parent_version=candidate.version,
        deprecation=reason,
        history=candidate.history + (candidate,),
    )


def rollback_to(candidate: CandidateRecord) -> CandidateRecord | None:
    """Return the immediate previous version, or ``None`` when none exists."""
    if not candidate.history:
        return None
    return candidate.history[-1]