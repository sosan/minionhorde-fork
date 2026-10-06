"""Tests for task 10.16 — condition-content verification.

Every record verifies that ``memory_injected`` and ``criteria_injected``
match the condition label AND the injected content hashes. A mismatch is
marked ``condition_mismatch`` and the record is excluded from contrasts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.condition_verification import (
    exclude_condition_mismatch,
    verify_condition,
)


def _record(
    *,
    condition: str,
    memory_injected: bool,
    criteria_injected: bool,
    retrieved: dict | None = None,
) -> dict:
    return {
        "case_id": f"case-{condition}",
        "condition": condition,
        "outcome_status": "model_pass",
        "memory_injected": memory_injected,
        "criteria_injected": criteria_injected,
        "retrieved": retrieved or {"status": "none", "items": 0, "tokens": 0, "hashes": []},
    }


def test_base_condition_requires_no_injection() -> None:
    record = _record(condition="base", memory_injected=False, criteria_injected=False)
    verify_condition(record)
    assert record["condition_mismatch"] is None
    assert record["outcome_status"] == "model_pass"


def test_full_condition_requires_both_injections_with_content() -> None:
    record = _record(
        condition="full",
        memory_injected=True,
        criteria_injected=True,
        retrieved={"status": "present", "items": 1, "tokens": 5, "hashes": ["m" * 64]},
    )
    record["criteria_hash"] = "c" * 64
    verify_condition(record)
    assert record["condition_mismatch"] is None
    assert record["outcome_status"] == "model_pass"


def test_memory_label_without_content_is_a_mismatch() -> None:
    record = _record(
        condition="full",
        memory_injected=True,
        criteria_injected=True,
        retrieved={"status": "none", "items": 0, "tokens": 0, "hashes": []},
    )
    record["criteria_hash"] = "c" * 64
    verify_condition(record)
    assert record["condition_mismatch"] is not None
    assert "memory" in record["condition_mismatch"]
    assert record["outcome_status"] == "condition_mismatch"


def test_label_contradicting_condition_is_a_mismatch() -> None:
    record = _record(condition="base", memory_injected=True, criteria_injected=True)
    verify_condition(record)
    assert record["condition_mismatch"] is not None
    assert record["outcome_status"] == "condition_mismatch"


def test_criteria_missing_hash_is_a_mismatch() -> None:
    record = _record(
        condition="criteria",
        memory_injected=False,
        criteria_injected=True,
    )
    verify_condition(record)
    assert record["condition_mismatch"] is not None
    assert "criteria" in record["condition_mismatch"]
    assert record["outcome_status"] == "condition_mismatch"


def test_exclude_condition_mismatch_filters_contrasts() -> None:
    mismatched = _record(condition="base", memory_injected=True, criteria_injected=True)
    verify_condition(mismatched)
    valid = _record(condition="criteria", memory_injected=False, criteria_injected=True)
    valid["criteria_hash"] = "c" * 64
    verify_condition(valid)
    result = exclude_condition_mismatch([mismatched, valid])
    assert mismatched["case_id"] in result["excluded_case_ids"]
    assert valid["case_id"] not in result["excluded_case_ids"]
    assert result["eligible_contrast_count"] == 1


def test_exclude_condition_mismatch_never_removes_valid_records() -> None:
    records = [_record(condition="base", memory_injected=False, criteria_injected=False) for _ in range(3)]
    for record in records:
        verify_condition(record)
    result = exclude_condition_mismatch(records)
    assert result["excluded_case_ids"] == []
    assert result["eligible_contrast_count"] == 3