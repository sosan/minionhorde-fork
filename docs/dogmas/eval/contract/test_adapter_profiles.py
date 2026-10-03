"""Layer A/B profile capture through the provenance adapter (task 2.2).

The adapter must carry profile identifiers onto evaluation records without
changing any enforcement field, and must remain backward compatible (default
``"unknown"``) for callers that do not yet capture profiles.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.layer_profiles import capture_for_record, default_layer_a_profile, default_layer_b_profile
from contract.provenance_adapter import adapt_result, adapt_result_with_profiles
from contract.schema_store import SchemaStore

MANUAL = {
    "case_id": "synthetic/secret-redaction-001",
    "case_version": "v1",
    "classification": "PASS",
    "requested_model": "m",
    "served_model": "m",
    "sampling": "temperature=0",
}


@pytest.fixture()
def store() -> SchemaStore:
    return SchemaStore()


def test_default_capture_stays_unknown_for_legacy_callers() -> None:
    result = adapt_result(MANUAL, condition="C0")
    assert result["layer_a_profile"] == "unknown"
    assert result["layer_b_criteria_version"] == "unknown"
    assert result["layer_c_memory_version"] == "unknown"


def test_adapt_result_carries_profiles_verbatim() -> None:
    result = adapt_result(
        MANUAL,
        condition="C0",
        layer_a_profile="layer-a/default@v4.1",
        layer_b_criteria_version="v4.1+layer-b/dogmas-core@v4.1+security@v1",
        layer_c_memory_version="n/a",
    )
    assert result["layer_a_profile"] == "layer-a/default@v4.1"
    assert result["layer_b_criteria_version"] == "v4.1+layer-b/dogmas-core@v4.1+security@v1"
    assert result["layer_c_memory_version"] == "n/a"


def test_adapt_result_with_profiles_carries_capture() -> None:
    layer_a = default_layer_a_profile()
    layer_b = default_layer_b_profile()
    captured = capture_for_record(layer_a, layer_b)
    result = adapt_result_with_profiles(MANUAL, condition="C0", **captured)
    assert result["layer_a_profile"] == captured["layer_a_profile"]
    assert result["layer_b_criteria_version"] == captured["layer_b_criteria_version"]


def test_capture_never_changes_enforcement_fields() -> None:
    layer_a = default_layer_a_profile()
    layer_b = default_layer_b_profile()
    captured = capture_for_record(layer_a, layer_b)
    plain = adapt_result(MANUAL, condition="C1")
    profiled = adapt_result(MANUAL, condition="C1", **captured)
    for field in ("condition", "evidence_mode", "outcome_status", "provenance_status", "comparability"):
        assert plain[field] == profiled[field], field


def test_profiled_result_is_schema_valid(store: SchemaStore) -> None:
    layer_a = default_layer_a_profile()
    layer_b = default_layer_b_profile()
    captured = capture_for_record(layer_a, layer_b)
    result = adapt_result(MANUAL, condition="C2", **captured)
    store.validate("evaluation_result", result)


def test_profile_capture_with_literal_response_stays_valid(store: SchemaStore) -> None:
    layer_a = default_layer_a_profile()
    layer_b = default_layer_b_profile()
    captured = capture_for_record(layer_a, layer_b)
    result = adapt_result(
        MANUAL,
        condition="C3",
        response_literal="independent read confirms feature_enabled=false after re-apply",
        **captured,
    )
    assert result["evidence_mode"] == "literal"
    store.validate("evaluation_result", result)