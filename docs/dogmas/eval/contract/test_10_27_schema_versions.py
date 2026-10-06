"""Tests for task 10.27 — schema versioning with versioned readers.

Artifacts are read through version-aware readers; migrations produce
separately hashed migration artifacts and never rewrite the original in
place. When a migration loses semantic meaning, claims are downgraded.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.schema_versions import (
    VersionedReader,
    downgrade_claims,
    migrate_artifact,
)


def test_versioned_reader_registers_and_reads_versions() -> None:
    reader = VersionedReader()
    reader.register("v1", lambda doc: {"version": "v1", "value": doc["value"]})
    reader.register("v2", lambda doc: {"version": "v2", "value": doc["value"], "extra": doc.get("extra")})
    assert reader.read("v1", {"value": 1}) == {"version": "v1", "value": 1}
    assert reader.read("v2", {"value": 1, "extra": 2}) == {"version": "v2", "value": 1, "extra": 2}


def test_versioned_reader_rejects_unknown_version() -> None:
    reader = VersionedReader()
    reader.register("v1", lambda doc: doc)
    with pytest.raises(KeyError, match="version"):
        reader.read("v3", {"value": 1})


def test_migrate_artifact_never_rewrites_original() -> None:
    original = {"schema_version": "legacy", "case_id": "case-01", "recovery": 0.7}
    artifact = migrate_artifact(original, from_version="legacy", to_version="v1", lossy_semantics=["recovery_dimension_renamed"])
    assert original["case_id"] == "case-01"
    assert artifact["source_version"] == "legacy"
    assert artifact["target_version"] == "v1"
    assert artifact["migration_hash"] != artifact["source_hash"]
    assert artifact["lossy_semantics"] == ["recovery_dimension_renamed"]


def test_migration_artifact_is_separately_hashed() -> None:
    original = {"schema_version": "legacy", "case_id": "case-01", "recovery": 0.7}
    a = migrate_artifact(original, from_version="legacy", to_version="v1", lossy_semantics=[])
    b = migrate_artifact(original, from_version="legacy", to_version="v1", lossy_semantics=[])
    assert a == b
    assert a["source_hash"] != a["migration_hash"]
    assert len(a["migration_hash"]) == 64


def test_lossless_migration_keeps_claims() -> None:
    original = {"schema_version": "legacy", "case_id": "case-01", "classification": "PASS"}
    artifact = migrate_artifact(original, from_version="legacy", to_version="v1", lossy_semantics=[])
    claims = downgrade_claims(artifact)
    assert claims["eligible_claims"] == {
        "descriptive_report": True,
        "causal": False,
        "transfer": False,
        "promotion": False,
        "layer_c_improvement": False,
    }
    assert claims["comparability"] == "non_comparable"


def test_lossy_migration_downgrades_to_descriptive_only() -> None:
    original = {"schema_version": "legacy", "case_id": "case-01", "recovery": 0.7}
    artifact = migrate_artifact(
        original,
        from_version="legacy",
        to_version="v1",
        lossy_semantics=["recovery_dimension_renamed"],
    )
    claims = downgrade_claims(artifact)
    assert claims["eligible_claims"]["descriptive_report"] is True
    assert claims["eligible_claims"]["causal"] is False
    assert claims["eligible_claims"]["transfer"] is False
    assert claims["eligible_claims"]["promotion"] is False
    assert claims["eligible_claims"]["layer_c_improvement"] is False
    assert claims["downgraded"] == ["recovery_dimension_renamed"]


def test_lossy_migration_marks_record_limited() -> None:
    artifact = migrate_artifact(
        {"schema_version": "legacy", "case_id": "case-01", "recovery": 0.7},
        from_version="legacy",
        to_version="v1",
        lossy_semantics=["recovery_dimension_renamed"],
    )
    claims = downgrade_claims(artifact)
    assert claims["provenance_status"] == "limited"
    assert claims["evidence_mode"] == "summary"