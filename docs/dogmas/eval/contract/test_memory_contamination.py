"""Task 5.8: memory-condition results are contaminated when an evaluation
case overlaps a memory episode supporting an active candidate; contaminated
cases are excluded from transfer claims."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from memory_contamination import (
    MemoryEpisode,
    mark_memory_condition_contamination,
    exclude_contaminated_from_transfer,
)


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _result(case_id: str, case_hash: str, condition: str) -> dict:
    return {"case_id": case_id, "case_hash": case_hash, "condition": condition}


def test_memory_condition_overlap_is_marked_contaminated() -> None:
    case_hash = _h("case-overlap")
    episode = MemoryEpisode(
        episode_id="ep-1",
        case_hashes=(case_hash,),
        supporting_candidate_ids=("cand-active",),
    )
    results = [_result("c-1", case_hash, "full")]
    marked = mark_memory_condition_contamination(results, [episode], active_candidate_ids={"cand-active"})
    assert marked[0]["contaminated"] is True
    assert marked[0]["contamination_reason"] == "case overlaps episode ep-1 supporting active candidate cand-active"


def test_criteria_only_condition_is_not_contaminated() -> None:
    case_hash = _h("case-criteria")
    episode = MemoryEpisode(episode_id="ep-1", case_hashes=(case_hash,), supporting_candidate_ids=("cand-active",))
    results = [_result("c-2", case_hash, "criteria")]
    marked = mark_memory_condition_contamination(results, [episode], active_candidate_ids={"cand-active"})
    assert marked[0]["contaminated"] is False


def test_inactive_candidate_does_not_contaminate() -> None:
    case_hash = _h("case-inactive")
    episode = MemoryEpisode(episode_id="ep-1", case_hashes=(case_hash,), supporting_candidate_ids=("cand-archived",))
    results = [_result("c-3", case_hash, "full")]
    marked = mark_memory_condition_contamination(results, [episode], active_candidate_ids={"cand-active"})
    assert marked[0]["contaminated"] is False


def test_non_overlapping_memory_case_stays_clean() -> None:
    episode = MemoryEpisode(episode_id="ep-1", case_hashes=(_h("other"),), supporting_candidate_ids=("cand-active",))
    results = [_result("c-4", _h("distinct"), "full")]
    marked = mark_memory_condition_contamination(results, [episode], active_candidate_ids={"cand-active"})
    assert marked[0]["contaminated"] is False


def test_contaminated_cases_excluded_from_transfer_claims() -> None:
    clean = _result("c-clean", _h("clean"), "full")
    dirty = _result("c-dirty", _h("dirty"), "full")
    episode = MemoryEpisode(episode_id="ep-1", case_hashes=(_h("dirty"),), supporting_candidate_ids=("cand-active",))
    marked = mark_memory_condition_contamination([clean, dirty], [episode], active_candidate_ids={"cand-active"})
    report = exclude_contaminated_from_transfer(marked)
    assert [r["case_id"] for r in report["eligible"]] == ["c-clean"]
    assert report["excluded_case_ids"] == ["c-dirty"]
    assert report["eligible_transfer_count"] == 1


def test_episode_requires_hashes_or_ids() -> None:
    with pytest.raises(ValueError, match="episode"):
        MemoryEpisode(episode_id="ep-1", case_hashes=(), supporting_candidate_ids=("cand-1",))