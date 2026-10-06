"""Tests for task 9.8 — split provenance hashes and attribution.

The provenance envelope records a content hash per role: case,
prompt_template, assembled_context, criteria, memory, policy, and
partition_manifest. Changing exactly one component MUST change exactly
one role hash; identical components MUST hash identically. The
``attribute_change`` function MUST return the single role that changed
between two splits; if more than one role changed it MUST raise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from contract.provenance_split import (
    PROVENANCE_ROLES,
    attribute_change,
    split_provenance,
)


def base_components() -> dict[str, object]:
    return {
        "case": {"case_id": "synthetic/case", "case_version": "v1"},
        "prompt_template": {"template": "fixture-template-v1"},
        "assembled_context": {"context": "fixture-context-v1", "condition": "full"},
        "criteria": {"profile_id": "fixture-b-v1"},
        "memory": {"candidate_id": "candidate-1"},
        "policy": {"policy": "vertical_slice", "version": "v1"},
        "partition_manifest": {"partition": "validation", "version": "v1"},
    }


def test_provenance_roles_list_is_seven() -> None:
    assert PROVENANCE_ROLES == (
        "case", "prompt_template", "assembled_context", "criteria",
        "memory", "policy", "partition_manifest",
    )


def test_split_returns_one_hash_per_role() -> None:
    split = split_provenance(base_components())
    assert set(split) == set(PROVENANCE_ROLES)
    for role, value in split.items():
        assert isinstance(value, str)
        assert len(value) == 64


def test_identical_components_produce_identical_splits() -> None:
    a = split_provenance(base_components())
    b = split_provenance(base_components())
    assert a == b


def test_changing_one_component_changes_exactly_one_hash() -> None:
    before = split_provenance(base_components())
    new_components = base_components()
    new_components["policy"] = {"policy": "full_suite", "version": "v1"}
    after = split_provenance(new_components)
    diff = [role for role in PROVENANCE_ROLES if before[role] != after[role]]
    assert diff == ["policy"]


def test_attribute_change_reports_single_role() -> None:
    before = split_provenance(base_components())
    new_components = base_components()
    new_components["memory"] = {"candidate_id": "candidate-2"}
    after = split_provenance(new_components)
    assert attribute_change(before, after) == "memory"


def test_attribute_change_raises_on_multiple_role_diffs() -> None:
    before = split_provenance(base_components())
    new_components = base_components()
    new_components["case"] = {"case_id": "synthetic/other-case", "case_version": "v1"}
    new_components["policy"] = {"policy": "full_suite", "version": "v1"}
    after = split_provenance(new_components)
    with pytest.raises(ValueError, match="multiple"):
        attribute_change(before, after)


def test_attribute_change_raises_on_no_diff() -> None:
    before = split_provenance(base_components())
    after = split_provenance(base_components())
    with pytest.raises(ValueError, match="no"):
        attribute_change(before, after)