"""Tests for task 9.2 — EvaluationResult schema completeness.

The record produced by ``adapt_result`` MUST emit a ``missingness`` object
describing which key fields are absent or ``None``. The schema accepts the
field; downstream consumers (9.4 outcome partitioning, 9.7 fixtures) rely
on it to separate model-outcome denominators from environment failures.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.provenance_adapter import adapt_result
from contract.schema_store import SchemaStore


@pytest.fixture()
def store() -> SchemaStore:
    return SchemaStore()


def manual_result(**overrides: object) -> dict:
    result = {
        "case_id": "synthetic/sandbox-postcondition-001",
        "case_version": "v1",
        "classification": "PASS",
        "requested_model": "claude-opus-5-max",
        "served_model": "unknown",
        "sampling": "unknown",
    }
    result.update(overrides)
    return result


def test_adapted_record_emits_missingness_object(store: SchemaStore) -> None:
    result = adapt_result(manual_result(), condition="C0", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert "missingness" in result
    assert isinstance(result["missingness"], dict)


def test_missingness_flags_unknown_served_model(store: SchemaStore) -> None:
    result = adapt_result(manual_result(), condition="C0", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert result["missingness"]["served_model"] is True
    assert result["missingness"]["sampling"] is True


def test_missingness_clears_when_metadata_is_reported(store: SchemaStore) -> None:
    enriched = manual_result(
        served_model="claude-opus-5-max",
        sampling="temperature=0,top_p=1",
        configuration_mismatch=False,
    )
    result = adapt_result(enriched, condition="C0", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert result["missingness"]["served_model"] is False
    assert result["missingness"]["sampling"] is False


def test_missingness_records_evidence_reference_absence(store: SchemaStore) -> None:
    result = adapt_result(manual_result(), condition="C0", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert result["missingness"]["evidence_reference"] is True