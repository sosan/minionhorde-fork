"""Frozen regression manifests (task 5.12).

A regression manifest freezes the list of regression cases (identifier +
version) at the time a recovery or promotion run starts and binds them to a
content hash. Every recovery/promotion result must reference the manifest
hash it ran against; a result without a reference, or with a mismatched
one, is unverifiable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

_REQUIRED_KEYS = ("case_id", "case_version")


def _canonical_case_list(cases: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    normalized = []
    for case in cases:
        for key in _REQUIRED_KEYS:
            if key not in case:
                raise ValueError(f"manifest case missing required key: {key}")
        normalized.append({"case_id": str(case["case_id"]), "case_version": str(case["case_version"])})
    normalized.sort(key=lambda item: (item["case_id"], item["case_version"]))
    return normalized


def _hash(cases: list[dict[str, str]]) -> str:
    canonical = json.dumps(cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_regression_manifest(cases: Iterable[Mapping[str, Any]], manifest_id: str) -> dict[str, Any]:
    """Build a frozen, content-hashed regression manifest.

    The same case set always yields the same hash regardless of input
    order (sorted canonical list); changing any case id or version changes
    the hash.
    """
    if not manifest_id:
        raise ValueError("manifest_id is required")
    frozen = _canonical_case_list(cases)
    if not frozen:
        raise ValueError("regression manifest cases list is empty; at least one case is required")
    return {
        "manifest_id": manifest_id,
        "manifest_hash": _hash(frozen),
        "case_count": len(frozen),
        "cases": frozen,
        "frozen": True,
    }


def verify_manifest_reference(result: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify a result references the manifest it claims to have run against."""
    reference = result.get("regression_manifest_hash")
    if reference is None:
        return {"verified": False, "unverifiable": True, "reason": "no reference to regression manifest"}
    if reference != manifest["manifest_hash"]:
        return {"verified": False, "unverifiable": True, "reason": "reference does not match manifest hash"}
    return {"verified": True, "unverifiable": False, "reason": None}


def check_manifest_reference(result: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Downgrade a recovery/promotion result to unverifiable when its
    manifest reference is absent or mismatched."""
    verification = verify_manifest_reference(result, manifest)
    return {
        "result_id": result.get("result_id"),
        "verification_status": "verified" if verification["verified"] else "unverifiable",
        **verification,
    }