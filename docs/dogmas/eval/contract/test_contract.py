from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.fixtures import evaluation_fixture, legacy_limited_fixture, trajectory_fixture
from contract.integrity import build_chain, build_manifest, verify_chain
from contract.schema_store import SchemaStore, SchemaValidationError


@pytest.fixture()
def store():
    return SchemaStore()


def test_all_modern_schemas_validate(store):
    store.validate("trajectory", trajectory_fixture())
    store.validate("evaluation_result", evaluation_fixture())
    store.validate("partition_manifest", {
        "schema_version": "v1", "partition": "validation", "content_hash": "a" * 64,
        "cases": [{"case_id": "case-1", "case_version": "v1", "case_hash": "b" * 64}],
    })
    store.validate("evaluation_policy", {
        "schema_version": "v1", "profile": "vertical_slice", "policy_hash": "a" * 64,
        "coverage": {"min_transfer_cases_per_variant": 1, "min_samples_per_category": 1},
        "agreement": {"statistic": "cohen_kappa", "threshold": 0.8, "min_subset_size": 3},
    })
    store.validate("evidence_custody", {
        "custody_id": "custody-1",
        "state": "OPEN",
        "created_at": "2026-09-29T00:00:00+00:00",
        "frozen_at": None,
        "amended_at": None,
        "superseded_at": None,
        "corrupted_at": None,
        "stored_literal_expires_at": None,
        "artifacts": {"case": {"role": "case", "path": "case.md", "content_hash": "a" * 64}},
        "literal_response_hash": None,
        "notes": "",
    })


def test_invalid_modern_result_is_rejected(store):
    result = evaluation_fixture()
    result["pair_key"] = None
    with pytest.raises(SchemaValidationError):
        store.validate("evaluation_result", result)


def test_hash_chain_and_manifest_verify():
    entries = build_chain([{"turn_id": "1", "state": "INIT"}, {"turn_id": "2", "state": "AUDIT"}])
    manifest = build_manifest("t-1", entries)
    assert verify_chain(entries, manifest)


def test_hash_chain_detects_payload_mutation():
    entries = build_chain([{"turn_id": "1", "state": "INIT"}, {"turn_id": "2", "state": "AUDIT"}])
    manifest = build_manifest("t-1", entries)
    mutated = copy.deepcopy(entries)
    mutated[0]["state"] = "CORRECT"
    result = verify_chain(mutated, manifest)
    assert not result.ok
    assert any("content_hash mismatch" in reason for reason in result.reasons)


def test_hash_chain_detects_reordering():
    entries = build_chain([{"turn_id": "1", "state": "INIT"}, {"turn_id": "2", "state": "AUDIT"}])
    manifest = build_manifest("t-1", entries)
    result = verify_chain(list(reversed(entries)), manifest)
    assert not result.ok


def test_empty_retrieval_is_explicit():
    record = trajectory_fixture(retrieved_status="none")
    assert record["retrieved"]["status"] == "none"
    assert record["retrieved"]["items"] == 0
    assert record["memory_injected"] is False


def test_legacy_fixture_is_limited():
    legacy = legacy_limited_fixture()
    assert legacy["provenance_status"] == "legacy_limited"
    assert legacy["classification_authority"] == "unverified"
    assert legacy["served_model"] == "unknown"
