from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from evidence_custody import CustodyError, create_custody, enforce_frozen_immutability, resolve_custody


def test_create_and_resolve_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "prompt.txt"
    artifact.write_text("stable prompt\n", encoding="utf-8")
    custody = create_custody("c-1", {"prompt_template": artifact})
    result = resolve_custody(custody)
    assert result["state"] == "OPEN"
    assert result["missing"] == []
    assert result["modified"] == []
    assert result["provenance_status"] == "verified"


def test_modified_artifact_marks_corrupted(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("before", encoding="utf-8")
    custody = create_custody("c-2", {"case": artifact})
    artifact.write_text("after", encoding="utf-8")
    result = resolve_custody(custody)
    assert result["modified"] == ["case"]
    assert result["state"] == "CORRUPTED"
    assert result["provenance_status"] == "unverified"


def test_missing_artifact_marks_corrupted(tmp_path: Path) -> None:
    artifact = tmp_path / "missing.txt"
    artifact.write_text("content", encoding="utf-8")
    custody = create_custody("c-3", {"case": artifact})
    artifact.unlink()
    result = resolve_custody(custody)
    assert result["missing"] == ["case"]
    assert result["state"] == "CORRUPTED"
    assert result["evidence_mode"] == "none"


def test_literal_expiry_downgrades_to_hash_only() -> None:
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    custody = create_custody("c-4", {}, literal_response="literal", literal_expires_at=expired)
    result = resolve_custody(custody)
    assert result["literal_expired"] is True
    assert result["evidence_mode"] == "hash_only"
    assert result["provenance_status"] == "limited"


def test_frozen_custody_is_immutable(tmp_path: Path) -> None:
    artifact = tmp_path / "policy.json"
    artifact.write_text("{}", encoding="utf-8")
    custody = create_custody("c-5", {"policy": artifact})
    custody.freeze()
    with pytest.raises(CustodyError, match="immutable"):
        enforce_frozen_immutability(custody, {"new": artifact})


def test_open_custody_rejects_duplicate_role(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("case", encoding="utf-8")
    custody = create_custody("c-6", {"case": artifact})
    with pytest.raises(CustodyError, match="already registered"):
        enforce_frozen_immutability(custody, {"case": artifact})


def test_inline_literal_is_hashed_without_persisting_content() -> None:
    custody = create_custody("c-7", {}, literal_response="secret-free literal")
    result = resolve_custody(custody)
    assert custody.literal_response_hash is not None
    assert result["resolved"]["response_literal"] == custody.literal_response_hash
