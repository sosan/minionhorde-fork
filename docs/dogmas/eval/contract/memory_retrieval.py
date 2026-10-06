"""Memory retrieval recording and exclusion (task 10.15).

Every evaluation/trajectory record carries a ``retrieved`` field that
captures whether memory was actually fetched for the case, how many
items, their hashes, and the token cost. Empty-retrieval cases under a
memory-using condition are marked ``no_memory_retrieved`` and excluded
from contrasts whose signal depends on the memory channel.
"""

from __future__ import annotations

from typing import Any, Iterable


MEMORY_CONDITIONS: frozenset[str] = frozenset({"full", "memory"})

DEFAULT_MEMORY_CONTRASTS: tuple[str, ...] = ("full_vs_criteria", "full_vs_memory")

OUTCOME_NO_MEMORY_RETRIEVED = "no_memory_retrieved"


def record_retrieval(
    record: dict[str, Any],
    *,
    items: Iterable[Any],
    hashes: Iterable[str],
    tokens: int,
) -> dict[str, Any]:
    """Replace ``record['retrieved']`` with a populated retrieval record."""
    record["retrieved"] = {
        "status": "present",
        "items": sum(1 for _ in items),
        "hashes": list(hashes),
        "tokens": int(tokens),
    }
    return record


def is_empty_retrieval(record: dict[str, Any]) -> bool:
    """True when memory was not actually fetched for this record."""
    retrieved = record.get("retrieved")
    if not retrieved:
        return True
    return retrieved.get("status") == "none"


def mark_empty_retrieval(record: dict[str, Any]) -> dict[str, Any]:
    """Mark a memory-condition record whose retrieval was empty.

    Cases that are not under a memory-using condition are left alone:
    their baseline ``retrieved: none`` is expected.
    """
    if record.get("condition") not in MEMORY_CONDITIONS:
        return record
    if is_empty_retrieval(record):
        record["outcome_status"] = OUTCOME_NO_MEMORY_RETRIEVED
    return record


def exclude_empty_retrieval(
    records: Iterable[dict[str, Any]],
    *,
    contrasts: tuple[str, ...] = DEFAULT_MEMORY_CONTRASTS,
) -> dict[str, Any]:
    """Partition records by whether they may enter the memory contrasts.

    A record is excluded when ``outcome_status`` was marked
    ``no_memory_retrieved``; it stays in the eligible set otherwise.
    """
    excluded: list[str] = []
    eligible = 0
    for record in records:
        if record.get("outcome_status") == OUTCOME_NO_MEMORY_RETRIEVED:
            excluded.append(record["case_id"])
        else:
            eligible += 1
    return {
        "excluded_case_ids": excluded,
        "eligible_contrast_count": eligible,
        "contrasts": tuple(contrasts),
    }
