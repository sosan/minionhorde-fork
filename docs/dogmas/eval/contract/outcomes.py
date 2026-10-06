"""Separate environment failures from model outcomes (task 9.4).

Model-outcome denominators MUST NOT include environment failures
(provider error, timeout, credentials, budget, schema-invalid, pending,
blocked, aborted). Records whose ``outcome_status`` is not a model
outcome status belong to a separate denominator — the environment-failure
denominator — and never contribute to claim numerators at any scope.
"""

from __future__ import annotations

from typing import Any, Iterable

ENVIRONMENT_FAILURE_STATUSES = frozenset({
    "provider_error",
    "timeout",
    "credential_error",
    "budget_exceeded",
    "schema_invalid",
    "pending",
    "blocked",
    "aborted",
})

MODEL_OUTCOME_STATUSES = frozenset({
    "model_pass",
    "model_fail",
    "no_memory_retrieved",
    "condition_mismatch",
})


def is_environment_failure(outcome_status: str) -> bool:
    """Return True when the outcome is an environment failure."""
    return outcome_status in ENVIRONMENT_FAILURE_STATUSES


def is_model_outcome(outcome_status: str) -> bool:
    """Return True when the outcome is a model outcome (eligible denominator)."""
    return outcome_status in MODEL_OUTCOME_STATUSES


def partition_outcomes(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Split ``results`` into model outcomes and environment failures.

    Returns a dict with ``model_outcomes``, ``environment_failures``,
    ``unknown_statuses``, ``model_outcome_count``,
    ``environment_failure_count``, and ``unknown_count``. Unknown statuses
    are counted but never classified into either bucket; they are recorded
    so callers can flag them rather than silently absorbing them.
    """
    model_outcomes: list[dict[str, Any]] = []
    environment_failures: list[dict[str, Any]] = []
    unknown_statuses: list[str] = []

    for record in results:
        status = record.get("outcome_status", "unknown")
        if is_model_outcome(status):
            model_outcomes.append(record)
        elif is_environment_failure(status):
            environment_failures.append(record)
        else:
            unknown_statuses.append(status)
            environment_failures.append(record)

    return {
        "model_outcomes": model_outcomes,
        "environment_failures": environment_failures,
        "unknown_statuses": sorted(set(unknown_statuses)),
        "model_outcome_count": len(model_outcomes),
        "environment_failure_count": len(environment_failures),
        "unknown_count": len(unknown_statuses),
    }


def model_outcome_denominator(results: Iterable[dict[str, Any]]) -> int:
    """Return the count of records that count as a model outcome.

    Environment failures, pending records, and unknown statuses are NOT
    included. The denominator is zero when the slice contains only
    environment failures, so claims are blocked rather than silently
    passing on zero observations.
    """
    return sum(1 for record in results if is_model_outcome(record.get("outcome_status", "unknown")))