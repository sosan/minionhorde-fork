"""Tests for task 10.15 — memory retrieval recording and exclusion.

Every trajectory/result records memory retrieval (items, hashes, token
count, or ``retrieved: none``). Empty-retrieval cases are marked
``no_memory_retrieved`` and excluded from ``full_vs_criteria`` and
``full_vs_memory`` contrasts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.memory_retrieval import (
    exclude_empty_retrieval,
    is_empty_retrieval,
    mark_empty_retrieval,
    record_retrieval,
)


def _record(*, condition: str, retrieved: dict | None, case_id: str | None = None) -> dict:
    return {
        "case_id": case_id or f"case-{condition}",
        "condition": condition,
        "outcome_status": "model_pass",
        "retrieved": retrieved,
    }


def test_record_retrieval_sets_items_hashes_and_tokens() -> None:
    record = _record(condition="full", retrieved=None)
    record_retrieval(record, items=["entry-1"], hashes=["h" * 64], tokens=12)
    assert record["retrieved"]["status"] == "present"
    assert record["retrieved"]["items"] == 1
    assert record["retrieved"]["hashes"] == ["h" * 64]
    assert record["retrieved"]["tokens"] == 12


def test_is_empty_retrieval_detects_none_status() -> None:
    record = _record(condition="full", retrieved={"status": "none", "items": 0, "tokens": 0, "hashes": []})
    assert is_empty_retrieval(record) is True


def test_present_retrieval_is_not_empty() -> None:
    record = _record(condition="full", retrieved={"status": "present", "items": 1, "tokens": 5, "hashes": ["h" * 64]})
    assert is_empty_retrieval(record) is False


def test_mark_empty_retrieval_sets_no_memory_retrieved_outcome() -> None:
    record = _record(condition="full", retrieved={"status": "none", "items": 0, "tokens": 0, "hashes": []})
    mark_empty_retrieval(record)
    assert record["outcome_status"] == "no_memory_retrieved"


def test_mark_empty_retrieval_only_applies_to_memory_conditions() -> None:
    record = _record(condition="base", retrieved={"status": "none", "items": 0, "tokens": 0, "hashes": []})
    mark_empty_retrieval(record)
    assert record["outcome_status"] == "model_pass"


def test_mark_empty_retrieval_keeps_present_retrieval() -> None:
    record = _record(condition="full", retrieved={"status": "present", "items": 1, "tokens": 5, "hashes": ["h" * 64]})
    mark_empty_retrieval(record)
    assert record["outcome_status"] == "model_pass"


def test_exclude_empty_retrieval_removes_from_full_contrasts() -> None:
    empty = _record(case_id="case-full-empty", condition="full", retrieved={"status": "none", "items": 0, "tokens": 0, "hashes": []})
    mark_empty_retrieval(empty)
    full_with_memory = _record(
        case_id="case-full-present",
        condition="full",
        retrieved={"status": "present", "items": 1, "tokens": 5, "hashes": ["h" * 64]},
    )
    criteria = _record(condition="criteria", retrieved={"status": "none", "items": 0, "tokens": 0, "hashes": []})
    result = exclude_empty_retrieval([empty, full_with_memory, criteria])
    assert empty["case_id"] in result["excluded_case_ids"]
    assert full_with_memory["case_id"] not in result["excluded_case_ids"]
    assert criteria["case_id"] not in result["excluded_case_ids"]
    assert result["eligible_contrast_count"] == 2


def test_exclude_empty_retrieval_defaults_to_full_vs_contrasts() -> None:
    result = exclude_empty_retrieval([])
    assert result["contrasts"] == ("full_vs_criteria", "full_vs_memory")