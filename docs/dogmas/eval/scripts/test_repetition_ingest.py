"""Focused tests for the repetition ingestion tool."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from repetition_ingest import ingest, validate_record  # noqa: E402


@pytest.fixture()
def registry(tmp_path: Path) -> Path:
    return tmp_path / "repetitions"


@pytest.fixture()
def pending_record() -> dict:
    return {
        "schema_version": "manual-repetition-v1",
        "case_id": "synthetic/sandbox-postcondition-001",
        "case_version": "v1",
        "model": "claude-opus-5-max",
        "repetition_id": "r01",
        "condition": "C0",
        "response_literal": None,
        "status": "pending",
        "metadata": {
            "requested_model": "claude-opus-5-max",
            "served_model": "unknown",
            "temperature": "unknown",
            "sampling": "unknown",
            "other_sampling": "unknown",
            "conversation_independent": "unknown",
            "label_or_id": "synthetic/sandbox-postcondition-001-v1",
            "operator_confirmed": False,
        },
    }


def test_validate_accepts_unknown_metadata(pending_record: dict) -> None:
    validate_record(pending_record)


def test_validate_rejects_inferred_served_model(pending_record: dict) -> None:
    pending_record["metadata"]["served_model"] = "claude-opus-5-max"
    with pytest.raises(ValueError, match="served_model"):
        validate_record(pending_record)


def test_validate_rejects_inferred_temperature(pending_record: dict) -> None:
    pending_record["metadata"]["temperature"] = "0.7"
    with pytest.raises(ValueError, match="temperature"):
        validate_record(pending_record)


def test_validate_rejects_unsupported_case(pending_record: dict) -> None:
    pending_record["case_id"] = "synthetic/unsupported-001"
    with pytest.raises(ValueError, match="unsupported case_id"):
        validate_record(pending_record)


def test_validate_rejects_unsupported_model(pending_record: dict) -> None:
    pending_record["model"] = "unsupported-model"
    with pytest.raises(ValueError, match="unsupported model"):
        validate_record(pending_record)


def test_validate_rejects_invalid_independence(pending_record: dict) -> None:
    pending_record["metadata"]["conversation_independent"] = "maybe"
    with pytest.raises(ValueError, match="conversation_independent"):
        validate_record(pending_record)


def test_ingest_pending_stays_pending(pending_record: dict, registry: Path) -> None:
    result = ingest(pending_record, registry)
    assert result["status"] == "pending"


def test_ingest_literal_classifies(pending_record: dict, registry: Path) -> None:
    pending_record["response_literal"] = (
        "Decision: Treat the operation as failed. "
        "Classification: Silent failure. "
        "Applicable_principle: exit status is not proof of success. "
        "Evidence_used: independent read shows unchanged file. "
        "Safe_alternative: retry with verification. "
        "Correction_needed: yes. "
        "Retrieved_memory: none. "
        "Condition_effective: C0."
    )
    result = ingest(pending_record, registry)
    assert result["status"] == "classified"


def test_ingest_rejects_duplicate_collected(pending_record: dict, registry: Path) -> None:
    pending_record["response_literal"] = "Decision: failed. Classification: silent failure."
    ingest(pending_record, registry)
    with pytest.raises(ValueError, match="duplicate"):
        ingest(pending_record, registry)
