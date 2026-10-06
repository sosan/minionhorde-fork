"""Partition-policy mapping for evaluation manifests (task 10.2).

A partition manifest MUST record the policy mapping it was built under:

* ``vertical_slice``: minimal partitions with approved non-comparable reuse,
  no definitive claims until the case inventory grows.
* ``full_suite``: full partitions, non-comparable reuse forbidden, case
  inventory growth required, definitive claims allowed.

Profiles outside this table are not addressable; the builder refuses
unknown profiles rather than guessing.
"""

from __future__ import annotations

from typing import Any, Iterable

from .canonical import digest


_PARTITION_POLICIES: dict[str, dict[str, Any]] = {
    "vertical_slice": {
        "minimal_partitions": True,
        "non_comparable_reuse": "approved",
        "definitive_claims_allowed": False,
        "case_inventory_growth_required": False,
    },
    "full_suite": {
        "minimal_partitions": False,
        "non_comparable_reuse": "forbidden",
        "definitive_claims_allowed": True,
        "case_inventory_growth_required": True,
    },
}


def partition_policy_for(profile_id: str) -> dict[str, Any]:
    """Return the policy mapping for ``profile_id``.

    Raises ``KeyError`` for unknown profiles so callers cannot silently
    fall back to a default policy.
    """
    return dict(_PARTITION_POLICIES[profile_id])


def build_partition_manifest(
    profile_id: str,
    partition: str,
    cases: Iterable[dict],
) -> dict[str, Any]:
    """Build a partition manifest with the chosen policy recorded.

    The content hash is computed over the canonical serialization of the
    payload (excluding ``content_hash`` itself), so it is stable across
    processes and across rebuilds with the same inputs.
    """
    if profile_id not in _PARTITION_POLICIES:
        raise KeyError(f"unknown partition profile: {profile_id!r}")
    policy_body = {
        "profile_id": profile_id,
        **_PARTITION_POLICIES[profile_id],
    }
    payload: dict[str, Any] = {
        "schema_version": "v1",
        "partition": partition,
        "cases": [dict(case) for case in cases],
        "policy": policy_body,
    }
    manifest = dict(payload)
    manifest["content_hash"] = digest(payload)
    return manifest
