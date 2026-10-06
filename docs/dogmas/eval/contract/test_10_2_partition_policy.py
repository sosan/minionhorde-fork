"""Tests for task 10.2 — partition-policy mapping in manifests.

The vertical-slice profile uses minimal partitions with approved
non-comparable reuse; a full_suite grows the case inventory before
definitive claims. Every partition manifest MUST record the chosen
policy mapping.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.partition_policy import (
    build_partition_manifest,
    partition_policy_for,
)
from contract.schema_store import SchemaStore


@pytest.fixture()
def store() -> SchemaStore:
    return SchemaStore()


CASES = [
    {
        "case_id": "synthetic/security-boundary",
        "case_version": "v1",
        "case_hash": "a" * 64,
        "domain": "security",
        "variant_class": "direct",
    },
    {
        "case_id": "synthetic/permission-boundary",
        "case_version": "v1",
        "case_hash": "b" * 64,
        "domain": "authorization",
        "variant_class": "direct",
    },
]


def test_vertical_slice_policy_is_minimal_with_approved_reuse() -> None:
    policy = partition_policy_for("vertical_slice")
    assert policy["minimal_partitions"] is True
    assert policy["non_comparable_reuse"] == "approved"
    assert policy["definitive_claims_allowed"] is False
    assert policy["case_inventory_growth_required"] is False


def test_full_suite_policy_requires_case_growth() -> None:
    policy = partition_policy_for("full_suite")
    assert policy["minimal_partitions"] is False
    assert policy["non_comparable_reuse"] == "forbidden"
    assert policy["definitive_claims_allowed"] is True
    assert policy["case_inventory_growth_required"] is True


def test_unknown_profile_raises() -> None:
    with pytest.raises(KeyError):
        partition_policy_for("nonexistent-profile")


def test_vertical_slice_manifest_records_policy(store: SchemaStore) -> None:
    manifest = build_partition_manifest("vertical_slice", "validation", CASES)
    store.validate("partition_manifest", manifest)
    assert manifest["policy"]["profile_id"] == "vertical_slice"
    assert manifest["policy"]["non_comparable_reuse"] == "approved"
    assert manifest["partition"] == "validation"
    assert len(manifest["cases"]) == 2


def test_full_suite_manifest_records_growth_requirement(store: SchemaStore) -> None:
    manifest = build_partition_manifest("full_suite", "support", CASES)
    store.validate("partition_manifest", manifest)
    assert manifest["policy"]["profile_id"] == "full_suite"
    assert manifest["policy"]["case_inventory_growth_required"] is True


def test_manifest_content_hash_is_stable(store: SchemaStore) -> None:
    a = build_partition_manifest("vertical_slice", "validation", CASES)
    b = build_partition_manifest("vertical_slice", "validation", CASES)
    assert a["content_hash"] == b["content_hash"]


def test_manifest_content_hash_changes_with_partition() -> None:
    a = build_partition_manifest("vertical_slice", "validation", CASES)
    b = build_partition_manifest("vertical_slice", "transfer", CASES)
    assert a["content_hash"] != b["content_hash"]