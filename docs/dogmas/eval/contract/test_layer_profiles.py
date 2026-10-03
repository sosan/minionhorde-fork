from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.canonical import digest
from contract.layer_profiles import (
    DEFAULT_LAYER_A_CONTROLS,
    LAYER_A_CONTROL_NAMES,
    LayerAControl,
    LayerAProfile,
    LayerBCriterion,
    LayerBProfile,
    capture_for_record,
    default_layer_a_profile,
    default_layer_b_profile,
    validate_profile_pair,
)
from contract.schema_store import SchemaStore


@pytest.fixture()
def store() -> SchemaStore:
    return SchemaStore()


def test_layer_a_profile_to_record_is_schema_valid(store: SchemaStore) -> None:
    profile = default_layer_a_profile()
    record = profile.to_record()
    store.validate("layer_a_profile", record)


def test_layer_b_profile_to_record_is_schema_valid(store: SchemaStore) -> None:
    profile = default_layer_b_profile()
    record = profile.to_record()
    store.validate("layer_b_profile", record)


def test_layer_a_profile_hash_is_canonical_and_deterministic() -> None:
    profile = LayerAProfile(
        profile_id="layer-a/test@v1",
        controls=DEFAULT_LAYER_A_CONTROLS,
        created_at="2026-10-03T00:00:00+00:00",
    )
    first = profile.to_record()
    second = profile.to_record()
    assert first["profile_hash"] == second["profile_hash"]
    assert first["profile_hash"] == digest({key: value for key, value in first.items() if key != "profile_hash"})


def test_layer_a_profile_rejects_duplicate_control() -> None:
    with pytest.raises(ValueError):
        LayerAProfile(
            profile_id="layer-a/dup",
            controls=(
                LayerAControl("tool_permissions", True, "x", "v1"),
                LayerAControl("tool_permissions", True, "y", "v1"),
            ),
        )


def test_layer_a_profile_rejects_unknown_control() -> None:
    with pytest.raises(ValueError):
        LayerAControl("unknown_control", True, "x", "v1")


def test_layer_a_profile_rejects_empty_controls() -> None:
    with pytest.raises(ValueError):
        LayerAProfile(profile_id="layer-a/empty", controls=())


def test_layer_b_profile_hash_is_canonical_and_deterministic() -> None:
    profile = LayerBProfile(
        profile_id="layer-b/test@v1",
        criteria_version="v1",
        core_dogmas_version="v4.1",
        security_policy_version="v1",
        criteria=(
            LayerBCriterion("rule/a", "v1", True, "rule"),
            LayerBCriterion("incident/x", "v1", False, "incident"),
        ),
        created_at="2026-10-03T00:00:00+00:00",
    )
    first = profile.to_record()
    second = profile.to_record()
    assert first["profile_hash"] == second["profile_hash"]


def test_layer_b_profile_distinguishes_normative_from_incidents() -> None:
    profile = LayerBProfile(
        profile_id="layer-b/mixed",
        criteria_version="v1",
        core_dogmas_version="v4.1",
        security_policy_version="v1",
        criteria=(
            LayerBCriterion("rule/keep", "v1", True, "rule"),
            LayerBCriterion("incident/observe", "v1", False, "incident"),
        ),
    )
    assert "rule/keep" in profile.normative_rule_ids()
    assert "incident/observe" not in profile.normative_rule_ids()
    assert profile.has_normative("rule/keep")
    assert not profile.has_normative("incident/observe")


def test_capture_for_record_returns_descriptive_identifiers() -> None:
    layer_a = default_layer_a_profile()
    layer_b = default_layer_b_profile()
    captured = capture_for_record(layer_a, layer_b)
    assert captured["layer_a_profile"] == layer_a.profile_id
    assert "v4.1" in captured["layer_b_criteria_version"]
    assert captured["layer_c_memory_version"] == "n/a"


def test_capture_does_not_change_enforcement() -> None:
    layer_a = default_layer_a_profile()
    layer_b = default_layer_b_profile()
    captured = capture_for_record(layer_a, layer_b)
    assert "irreversible_confirmation" in layer_a.enabled_controls()
    assert set(captured.keys()) == {"layer_a_profile", "layer_b_criteria_version", "layer_c_memory_version"}


def test_validate_profile_pair_accepts_defaults() -> None:
    assert validate_profile_pair(default_layer_a_profile(), default_layer_b_profile()) == []


def test_validate_profile_pair_rejects_disabled_required_control() -> None:
    controls = tuple(
        LayerAControl(name, False if name == "secret_redaction" else True, "x", "v1")
        for name in LAYER_A_CONTROL_NAMES
    )
    profile = LayerAProfile(profile_id="layer-a/disabled-redaction", controls=controls)
    errors = validate_profile_pair(profile, default_layer_b_profile())
    assert any("secret_redaction" in error for error in errors)


def test_validate_profile_pair_rejects_layer_b_without_normative_criteria() -> None:
    profile = LayerBProfile(
        profile_id="layer-b/no-normative",
        criteria_version="v1",
        core_dogmas_version="v4.1",
        security_policy_version="v1",
        criteria=(LayerBCriterion("incident/only", "v1", False, "incident"),),
    )
    errors = validate_profile_pair(default_layer_a_profile(), profile)
    assert any("no normative criteria" in error for error in errors)


def test_layer_a_profile_sort_is_stable_for_hash() -> None:
    created_at = "2026-10-03T00:00:00+00:00"
    a = LayerAProfile(
        profile_id="layer-a/order",
        controls=(
            LayerAControl("tool_permissions", True, "x", "v1"),
            LayerAControl("audit_logging", True, "x", "v1"),
        ),
        created_at=created_at,
    )
    b = LayerAProfile(
        profile_id="layer-a/order",
        controls=(
            LayerAControl("audit_logging", True, "x", "v1"),
            LayerAControl("tool_permissions", True, "x", "v1"),
        ),
        created_at=created_at,
    )
    assert a.to_record()["profile_hash"] == b.to_record()["profile_hash"]