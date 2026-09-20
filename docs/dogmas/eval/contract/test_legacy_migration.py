from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.legacy_migration import is_legacy_result, migrate_result, migration_can_support

LEGACY = {
    "case_id": "case-01",
    "model": "legacy-model",
    "provider": "fixture",
    "classification": "PASS",
    "justification": "summary only",
    "timestamp": "2026-01-01T00:00:00Z",
    "dimensions": {"clarity": 0.9, "security": 0.8, "recovery": 0.7},
}


def test_legacy_detection():
    assert is_legacy_result(LEGACY)
    assert not is_legacy_result({"schema_version": "v1", "condition": "full"})


def test_migration_marks_limited_provenance():
    artifact = migrate_result(LEGACY)
    assert artifact["provenance_status"] == "legacy_limited"
    assert artifact["classification_authority"] == "unverified"
    assert artifact["served_model"] == "unknown"
    assert artifact["evidence_mode"] == "summary"


def test_migration_never_grants_modern_claims():
    artifact = migrate_result(LEGACY)
    assert migration_can_support(artifact, "descriptive_report") is True
    for claim in ("causal", "transfer", "promotion", "layer_c_improvement"):
        assert migration_can_support(artifact, claim) is False


def test_legacy_recovery_is_not_merged_with_learning_recovery():
    artifact = migrate_result(LEGACY)
    assert "legacy_recovery" in artifact["legacy_dimensions"]
    assert "recovery" not in artifact["legacy_dimensions"]


def test_modern_result_is_rejected_by_migrator():
    with pytest.raises(ValueError):
        migrate_result({"schema_version": "v1", "condition": "full"})


def test_migration_is_not_a_modern_result():
    artifact = migrate_result(LEGACY)
    assert artifact["artifact_type"] == "legacy_migration"
    assert artifact["comparability"] == "non_comparable"
