"""Tests for task 9.4 — separating environment failures from model outcomes.

Environment failures (provider_error, timeout, credential_error,
budget_exceeded, schema_invalid, pending, blocked, aborted) are NOT part
of the model-outcome denominator. ``partition_outcomes`` MUST split them
out; ``model_outcome_denominator`` MUST count only model outcomes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.outcomes import (
    MODEL_OUTCOME_STATUSES,
    ENVIRONMENT_FAILURE_STATUSES,
    model_outcome_denominator,
    partition_outcomes,
)


def _record(outcome_status: str) -> dict:
    return {
        "case_id": f"case-{outcome_status}",
        "condition": "base",
        "outcome_status": outcome_status,
        "classification": "PASS",
    }


def test_partition_splits_environment_failures_from_model_outcomes() -> None:
    records = [
        _record("model_pass"),
        _record("model_fail"),
        _record("timeout"),
        _record("provider_error"),
        _record("credential_error"),
        _record("blocked"),
    ]
    parts = partition_outcomes(records)
    assert {r["case_id"] for r in parts["model_outcomes"]} == {"case-model_pass", "case-model_fail"}
    assert {r["case_id"] for r in parts["environment_failures"]} == {
        "case-timeout", "case-provider_error", "case-credential_error", "case-blocked",
    }
    assert parts["environment_failure_count"] == 4
    assert parts["model_outcome_count"] == 2


def test_model_outcome_denominator_excludes_environment_failures() -> None:
    records = [_record(s) for s in ("model_pass", "model_fail", "timeout", "blocked", "credential_error")]
    assert model_outcome_denominator(records) == 2


def test_model_outcome_denominator_returns_zero_on_empty() -> None:
    assert model_outcome_denominator([]) == 0
    assert model_outcome_denominator([_record("timeout")]) == 0


def test_status_sets_are_disjoint() -> None:
    assert MODEL_OUTCOME_STATUSES & ENVIRONMENT_FAILURE_STATUSES == set()
    assert "model_pass" in MODEL_OUTCOME_STATUSES
    assert "model_fail" in MODEL_OUTCOME_STATUSES
    for status in (
        "provider_error", "timeout", "credential_error",
        "budget_exceeded", "schema_invalid", "pending", "blocked", "aborted",
    ):
        assert status in ENVIRONMENT_FAILURE_STATUSES


def test_partition_preserves_unknown_outcomes_with_a_warning_field() -> None:
    records = [_record("model_pass"), _record("some-future-status")]
    parts = partition_outcomes(records)
    assert parts["model_outcome_count"] == 1
    assert parts["environment_failure_count"] == 1
    assert "some-future-status" in parts["unknown_statuses"]