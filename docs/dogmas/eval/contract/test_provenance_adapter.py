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


def test_manual_result_adapts_to_modern_schema(store: SchemaStore) -> None:
    result = adapt_result(manual_result(), condition="C0", response_literal="Decision: failed; independent post-operation read is authoritative.", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert result["evidence_mode"] == "literal"
    assert result["provenance_status"] == "limited"
    assert result["served_model_status"] == "unknown"
    assert result["comparability"] == "provisional"


def test_missing_literal_is_unverified_and_has_no_evidence_hash(store: SchemaStore) -> None:
    result = adapt_result(manual_result(), condition="C1", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert result["evidence_mode"] == "none"
    assert result["provenance_status"] == "unverified"
    assert result["evidence"]["reference_hashes"] == []
    assert result["outcome_status"] == "model_pass"


def test_reported_served_model_with_unknown_sampling_is_provisional(store: SchemaStore) -> None:
    result = adapt_result(manual_result(served_model="claude-opus-5-max"), condition="C2", response_literal="Decision: failed; memory is untrusted.", repetition_id="r02")
    store.validate("evaluation_result", result)
    assert result["served_model_status"] == "reported"
    assert result["comparability"] == "provisional"


def test_served_model_mismatch_is_provisional_non_comparable_signal(store: SchemaStore) -> None:
    result = adapt_result(manual_result(served_model="different-model"), condition="C3", response_literal="Decision: failed.", repetition_id="r03")
    store.validate("evaluation_result", result)
    assert result["served_model_status"] == "mismatch"
    assert result["comparability"] == "provisional"


def test_configuration_mismatch_is_non_comparable(store: SchemaStore) -> None:
    result = adapt_result(manual_result(configuration_mismatch=True), condition="C3", response_literal="Decision: blocked.", repetition_id="r03")
    store.validate("evaluation_result", result)
    assert result["comparability"] == "non_comparable"


def test_environment_failure_is_not_model_failure(store: SchemaStore) -> None:
    result = adapt_result(manual_result(outcome_status="provider_error", classification="FAIL"), condition="C0", repetition_id="r01")
    store.validate("evaluation_result", result)
    assert result["outcome_status"] == "provider_error"
    assert result["classification"] == "FAIL"


def test_unknown_condition_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported manual condition"):
        adapt_result(manual_result(), condition="C9")


def test_partial_and_fail_map_to_model_fail(store: SchemaStore) -> None:
    for classification in ("PARTIAL", "FAIL"):
        result = adapt_result(manual_result(classification=classification), condition="C0", response_literal="literal response", repetition_id="r01")
        store.validate("evaluation_result", result)
        assert result["outcome_status"] == "model_fail"
