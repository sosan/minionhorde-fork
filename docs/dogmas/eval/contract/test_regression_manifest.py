"""Task 5.12: regression manifests are frozen, content-hashed case lists;
recovery/promotion results must reference the manifest hash they ran
against, and results without the reference are unverifiable."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from regression_manifest import (
    build_regression_manifest,
    check_manifest_reference,
    verify_manifest_reference,
)


CASES = [
    {"case_id": "c-1", "case_version": "v1"},
    {"case_id": "c-2", "case_version": "v1"},
    {"case_id": "c-3", "case_version": "v2"},
]


def test_manifest_hash_is_stable_and_order_independent() -> None:
    manifest_a = build_regression_manifest(CASES, manifest_id="manifest-1")
    manifest_b = build_regression_manifest(list(reversed(CASES)), manifest_id="manifest-1")
    assert manifest_a["manifest_hash"] == manifest_b["manifest_hash"]
    assert len(manifest_a["manifest_hash"]) == 64
    assert manifest_a["case_count"] == 3


def test_manifest_change_alters_hash() -> None:
    manifest_a = build_regression_manifest(CASES, manifest_id="manifest-1")
    changed = [{"case_id": "c-1", "case_version": "v2"}, {"case_id": "c-2", "case_version": "v1"}, {"case_id": "c-3", "case_version": "v2"}]
    manifest_b = build_regression_manifest(changed, manifest_id="manifest-1")
    assert manifest_a["manifest_hash"] != manifest_b["manifest_hash"]


def test_manifest_is_frozen_after_build() -> None:
    manifest = build_regression_manifest(CASES, manifest_id="manifest-1")
    assert manifest["frozen"] is True
    assert manifest["manifest_id"] == "manifest-1"


def test_matching_reference_is_verified() -> None:
    manifest = build_regression_manifest(CASES, manifest_id="manifest-1")
    result = {"result_id": "r-1", "regression_manifest_hash": manifest["manifest_hash"]}
    report = verify_manifest_reference(result, manifest)
    assert report["verified"] is True
    assert report["unverifiable"] is False


def test_missing_reference_is_unverifiable() -> None:
    manifest = build_regression_manifest(CASES, manifest_id="manifest-1")
    report = verify_manifest_reference({"result_id": "r-1"}, manifest)
    assert report["unverifiable"] is True
    assert "no reference" in report["reason"]


def test_wrong_reference_is_unverifiable() -> None:
    manifest_a = build_regression_manifest(CASES, manifest_id="manifest-1")
    manifest_b = build_regression_manifest([{"case_id": "x", "case_version": "v9"}], manifest_id="manifest-2")
    report = verify_manifest_reference({"result_id": "r-1", "regression_manifest_hash": manifest_b["manifest_hash"]}, manifest_a)
    assert report["unverifiable"] is True
    assert "does not match" in report["reason"]


def test_check_manifest_reference_downgrades_result() -> None:
    manifest = build_regression_manifest(CASES, manifest_id="manifest-1")
    good = check_manifest_reference({"result_id": "r-1", "regression_manifest_hash": manifest["manifest_hash"]}, manifest)
    assert good["verification_status"] == "verified"
    bad = check_manifest_reference({"result_id": "r-2"}, manifest)
    assert bad["verification_status"] == "unverifiable"
    assert bad["result_id"] == "r-2"


def test_empty_case_list_is_rejected() -> None:
    with pytest.raises(ValueError, match="cases"):
        build_regression_manifest([], manifest_id="manifest-empty")