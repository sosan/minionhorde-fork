"""Tests for task 9.7 — scenarios and fixtures.

Five scenarios must be supported by the contract:

1. pair-key construction (case + repetition + condition → pair_key, stable)
2. retry-after-failure (env failure then retry, retry is a separate pair)
3. legacy-limited label (already migrated; not eligible for modern claims)
4. environment-failure classification (recorded separately from model outcome)
5. claim-scope downgrade (vertical_slice downgrades candidate/dimension)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from contract.fixtures import (
    claim_scope_downgrade_fixture,
    environment_failure_fixture,
    pair_key_fixture,
    retry_after_failure_fixture,
)
from contract.legacy_migration import migrate_result, migration_can_support
from contract.outcomes import partition_outcomes
from contract.profiles import restrict_claim, vertical_slice_profile
from contract.coverage_gates import ClaimScope
from contract.schema_store import SchemaStore


@pytest.fixture()
def store() -> SchemaStore:
    return SchemaStore()


def test_pair_key_fixture_is_stable(store: SchemaStore) -> None:
    a = pair_key_fixture()
    b = pair_key_fixture()
    assert a["pair_key"] == b["pair_key"]
    assert a["pair_key"] == f"{a['case_id']}:{a['repetition_id']}:{a['condition']}"
    store.validate("evaluation_result", a)


def test_pair_key_changes_when_condition_changes() -> None:
    a = pair_key_fixture(condition="base")
    b = pair_key_fixture(condition="criteria")
    assert a["pair_key"] != b["pair_key"]


def test_retry_after_failure_separates_attempt_and_retry(store: SchemaStore) -> None:
    scenario = retry_after_failure_fixture()
    store.validate("evaluation_result", scenario["first_attempt"])
    store.validate("evaluation_result", scenario["retry"])
    assert scenario["first_attempt"]["outcome_status"] == "timeout"
    assert scenario["first_attempt"]["pair_key"].endswith(":base")
    assert scenario["retry"]["outcome_status"] == "model_pass"
    assert scenario["retry"]["pair_key"].endswith(":base")
    assert scenario["first_attempt"]["pair_key"] != scenario["retry"]["pair_key"]
    assert scenario["first_attempt"]["repetition_id"] != scenario["retry"]["repetition_id"]


def test_legacy_limited_label_does_not_support_modern_claims() -> None:
    legacy = {
        "case_id": "legacy/case-01",
        "model": "legacy-model",
        "provider": "fixture",
        "classification": "PASS",
        "justification": "summary only",
        "timestamp": "2026-01-01T00:00:00Z",
        "dimensions": {"recovery": 0.7},
    }
    migrated = migrate_result(legacy)
    assert migrated["provenance_status"] == "legacy_limited"
    assert migration_can_support(migrated, "causal") is False
    assert migration_can_support(migrated, "transfer") is False
    assert migration_can_support(migrated, "promotion") is False
    assert migration_can_support(migrated, "layer_c_improvement") is False
    assert migration_can_support(migrated, "descriptive_report") is True


def test_environment_failure_fixture_is_separated_from_model_outcomes(store: SchemaStore) -> None:
    record = environment_failure_fixture()
    store.validate("evaluation_result", record)
    parts = partition_outcomes([record])
    assert record["outcome_status"] in {"provider_error", "timeout", "credential_error", "budget_exceeded", "schema_invalid", "pending", "blocked", "aborted"}
    assert parts["model_outcome_count"] == 0
    assert parts["environment_failure_count"] == 1


def test_claim_scope_downgrade_fixture_is_downgraded_under_vertical_slice(store: SchemaStore) -> None:
    record = claim_scope_downgrade_fixture()
    store.validate("evaluation_result", record)
    profile = vertical_slice_profile()
    candidate = restrict_claim(profile, ClaimScope.CANDIDATE)
    dimension = restrict_claim(profile, ClaimScope.DIMENSION)
    global_scope = restrict_claim(profile, ClaimScope.GLOBAL)
    assert candidate["verdict"] == "preliminary"
    assert dimension["verdict"] == "preliminary"
    assert global_scope["verdict"] == "block"