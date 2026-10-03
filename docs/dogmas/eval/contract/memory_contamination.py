"""Contamination of memory-condition results (task 5.8).

A result runs under a memory condition (one of the conditions that inject
memory state) and is contaminated when its case overlaps a memory episode
that supports an active candidate: the case's outcome can be explained by
the very candidate it is meant to evaluate, so it cannot support claims
about transfer. Contaminated cases are excluded from transfer claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

MEMORY_CONDITIONS = frozenset({"full", "criteria_memory", "memory"})


@dataclass(frozen=True)
class MemoryEpisode:
    """A memory episode that may leak evaluation-case content into memory."""

    episode_id: str
    case_hashes: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()
    supporting_candidate_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id is required")
        if not self.case_hashes and not self.case_ids:
            raise ValueError("memory episode requires at least one case hash or case id")


def _overlaps(result: dict[str, Any], episode: MemoryEpisode) -> bool:
    case_hash = result.get("case_hash")
    case_id = result.get("case_id")
    return (case_hash is not None and case_hash in episode.case_hashes) or (
        case_id is not None and case_id in episode.case_ids
    )


def mark_memory_condition_contamination(
    results: list[dict[str, Any]],
    episodes: Iterable[MemoryEpisode],
    active_candidate_ids: set[str],
) -> list[dict[str, Any]]:
    """Mark results whose case overlaps an active-supported memory episode.

    Only results under a memory condition are eligible for contamination;
    criteria-only evaluations never inherit memory state.
    """
    marked: list[dict[str, Any]] = []
    for result in results:
        record = dict(result)
        record["contaminated"] = False
        record["contamination_reason"] = None
        if result.get("condition") not in MEMORY_CONDITIONS:
            marked.append(record)
            continue
        for episode in episodes:
            supported = set(episode.supporting_candidate_ids) & active_candidate_ids
            if _overlaps(result, episode) and supported:
                candidate = sorted(supported)[0]
                record["contaminated"] = True
                record["contamination_reason"] = (
                    f"case overlaps episode {episode.episode_id} supporting active candidate {candidate}"
                )
                break
        marked.append(record)
    return marked


def exclude_contaminated_from_transfer(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Split results into transfer-eligible and excluded (contaminated)."""
    eligible = [result for result in results if not result.get("contaminated")]
    excluded = [result for result in results if result.get("contaminated")]
    return {
        "eligible": eligible,
        "excluded": excluded,
        "excluded_case_ids": [result.get("case_id") for result in excluded],
        "eligible_transfer_count": len(eligible),
    }