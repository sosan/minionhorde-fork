"""Condition-content verification for evaluation records (task 10.16).

A record's condition label (``base`` / ``criteria`` / ``criteria_memory`` /
``full`` / ``memory``) declares what the experiment is supposed to inject
and what content hashes must accompany it. ``verify_condition`` checks
the label against the actual ``memory_injected``/``criteria_injected``
booleans AND the presence of the injected content. A mismatch is
recorded on the record and sets ``outcome_status`` to
``condition_mismatch`` so contrast building can exclude it.
"""

from __future__ import annotations

from typing import Any, Iterable

from .memory_retrieval import is_empty_retrieval


OUTCOME_CONDITION_MISMATCH = "condition_mismatch"

_MEMORY_LABELS: frozenset[str] = frozenset({"full", "memory", "criteria_memory"})
_CRITERIA_LABELS: frozenset[str] = frozenset({"criteria", "full", "criteria_memory"})


def _missing_memory_content(record: dict[str, Any]) -> bool:
    if not record.get("memory_injected"):
        return False
    return is_empty_retrieval(record)


def _missing_criteria_content(record: dict[str, Any]) -> bool:
    if not record.get("criteria_injected"):
        return False
    return not record.get("criteria_hash")


def verify_condition(record: dict[str, Any]) -> dict[str, Any]:
    """Verify that the record's content matches its condition label.

    On a mismatch, sets ``record['condition_mismatch']`` to a descriptive
    reason and ``record['outcome_status']`` to ``condition_mismatch``.
    On success, leaves ``condition_mismatch`` unset (or ``None``) and
    does not change ``outcome_status``.
    """
    condition = record.get("condition")
    problems: list[str] = []

    if condition == "base":
        if record.get("memory_injected"):
            problems.append("base condition must not inject memory")
        if record.get("criteria_injected"):
            problems.append("base condition must not inject criteria")
    elif condition == "full":
        if not record.get("memory_injected"):
            problems.append("full condition requires memory injection")
        elif _missing_memory_content(record):
            problems.append("memory label set but no memory content retrieved")
        if not record.get("criteria_injected"):
            problems.append("full condition requires criteria injection")
        elif _missing_criteria_content(record):
            problems.append("criteria label set but criteria content hash missing")
    elif condition == "criteria":
        if record.get("memory_injected"):
            problems.append("criteria condition must not inject memory")
        if not record.get("criteria_injected"):
            problems.append("criteria condition requires criteria injection")
        elif _missing_criteria_content(record):
            problems.append("criteria label set but criteria content hash missing")
    elif condition == "memory":
        if not record.get("memory_injected"):
            problems.append("memory condition requires memory injection")
        elif _missing_memory_content(record):
            problems.append("memory label set but no memory content retrieved")
    elif condition == "criteria_memory":
        if not record.get("memory_injected"):
            problems.append("criteria_memory condition requires memory injection")
        elif _missing_memory_content(record):
            problems.append("memory label set but no memory content retrieved")
        if not record.get("criteria_injected"):
            problems.append("criteria_memory condition requires criteria injection")
        elif _missing_criteria_content(record):
            problems.append("criteria label set but criteria content hash missing")
    else:
        problems.append(f"unknown condition label: {condition!r}")

    if problems:
        record["condition_mismatch"] = "; ".join(problems)
        record["outcome_status"] = OUTCOME_CONDITION_MISMATCH
    else:
        record["condition_mismatch"] = None
    return record


def exclude_condition_mismatch(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Partition records by whether they may enter contrast analysis.

    A record is excluded when ``outcome_status`` is ``condition_mismatch``;
    it stays in the eligible set otherwise.
    """
    excluded: list[str] = []
    eligible = 0
    for record in records:
        if record.get("outcome_status") == OUTCOME_CONDITION_MISMATCH:
            excluded.append(record["case_id"])
        else:
            eligible += 1
    return {
        "excluded_case_ids": excluded,
        "eligible_contrast_count": eligible,
    }
