"""Synthetic trajectory fixtures cover complete, interrupted, unverified,
and secret-redacted trajectories (task 1.3) without real credentials or
destructive actions.

The test asserts:
  * The four canonical flavors each have a JSON file in
    ``fixtures/valid/trajectory/`` that validates against the v1 trajectory
    schema.
  * The Python builders in ``contract.fixtures`` produce schema-valid
    dictionaries with the distinguishing markers (terminal_state,
    evaluation_validity, redaction marker, expired-literal placeholder).
  * The chain hashes round-trip through ``verify_chain`` and ``verify_manifest``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contract.fixtures import (
    redacted_trajectory_fixture,
    trajectory_fixture,
    unverified_trajectory_fixture,
)
from contract.integrity import verify_chain, verify_manifest
from contract.schema_store import SchemaStore

FLAVORS = {
    "full-completed": lambda: trajectory_fixture(terminal_state="COMPLETED", custody_state="FROZEN"),
    "full-interrupted": lambda: trajectory_fixture(terminal_state="ABORTED", custody_state="OPEN"),
    "unverified-expired-evidence": unverified_trajectory_fixture,
    "redacted-literal": redacted_trajectory_fixture,
}


@pytest.fixture()
def store() -> SchemaStore:
    return SchemaStore()


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "valid" / "trajectory"


def test_all_flavor_files_exist(fixtures_dir: Path) -> None:
    missing = [name for name in FLAVORS if not (fixtures_dir / f"{name}.json").is_file()]
    assert not missing, f"missing fixture files: {missing}"


@pytest.mark.parametrize("flavor", sorted(FLAVORS))
def test_flavor_file_is_schema_valid(flavor: str, fixtures_dir: Path, store: SchemaStore) -> None:
    document = json.loads((fixtures_dir / f"{flavor}.json").read_text(encoding="utf-8"))
    store.validate("trajectory", document)


@pytest.mark.parametrize("flavor", sorted(FLAVORS))
def test_flavor_builder_is_schema_valid(flavor: str, store: SchemaStore) -> None:
    fixture = FLAVORS[flavor]()
    store.validate("trajectory", fixture)


@pytest.mark.parametrize("flavor", sorted(FLAVORS))
def test_flavor_chain_is_verifiable(flavor: str) -> None:
    fixture = FLAVORS[flavor]()
    result = verify_chain(fixture["entries"], fixture["manifest"])
    assert result.ok, result.reasons
    manifest_errors = verify_manifest(fixture["manifest"], fixture["entries"], fixture["trajectory_id"])
    assert not manifest_errors, manifest_errors


def test_unverified_carries_expired_literal_marker(fixtures_dir: Path) -> None:
    fixture = json.loads((fixtures_dir / "unverified-expired-evidence.json").read_text(encoding="utf-8"))
    summary = fixture["entries"][-1]["summary"]
    assert summary["evidence_mode"] == "hash_only"
    assert "stored_literal_expires_at" in summary
    assert summary["stored_literal_expires_at"] < "2026-01-01T00:00:00Z"
    assert fixture["evaluation_validity"] == "limited"


def test_redacted_uses_marker_and_no_real_credential(fixtures_dir: Path) -> None:
    fixture = json.loads((fixtures_dir / "redacted-literal.json").read_text(encoding="utf-8"))
    summary = fixture["entries"][-1]["summary"]
    assert summary["literal_redacted"] is True
    marker = summary["redaction_marker"]
    assert "REDACTED" in marker
    assert "ghp_" not in marker
    assert "sk-" not in marker
    assert "xox" not in marker
    assert "AKIA" not in marker
    text = json.dumps(fixture, ensure_ascii=False)
    assert "ghp_" not in text
    assert "sk-" not in text
    assert fixture["evaluation_validity"] == "limited"


def test_unverified_and_redacted_use_distinct_content_hashes(fixtures_dir: Path) -> None:
    a = json.loads((fixtures_dir / "unverified-expired-evidence.json").read_text(encoding="utf-8"))
    b = json.loads((fixtures_dir / "redacted-literal.json").read_text(encoding="utf-8"))
    assert a["case_hash"] != b["case_hash"]
    assert a["manifest"]["manifest_hash"] != b["manifest"]["manifest_hash"]
    assert a["trajectory_id"] != b["trajectory_id"]