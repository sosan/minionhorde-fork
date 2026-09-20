"""Append-only hash-chain integrity for trajectory records.

Implements the contract in the operational-learning spec
("Append-only integrity is verifiable") and design decision 1:

- each entry carries a ``content_hash`` (its payload, excluding the integrity
  fields) and a ``prev_hash`` (the previous entry's ``content_hash``)
- a versioned manifest anchors the sequence: trajectory id, entry count,
  first/last content hashes, hash algorithm, canonicalization version, and a
  manifest hash computed over the manifest without its own hash
- verification recomputes canonical bytes and hashes before a result derived
  from the trajectory is trusted; mutation, reordering, truncation, and
  corruption are detected

This provides integrity within the trusted storage domain. It is not an
adversarial barrier (see the design's scope note).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import CANONICAL_VERSION, HASH_ALGORITHM, canonical_bytes, content_hash, digest

GENESIS_PREV = None


@dataclass
class VerifyResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def build_entry(payload: dict) -> dict:
    """Return an entry with ``content_hash`` and ``prev_hash`` set.

    ``prev_hash`` must be supplied in ``payload`` (``None`` for genesis) or
    via the ``prev_hash`` parameter after construction.
    """
    prev = payload.get("prev_hash", GENESIS_PREV)
    entry = {key: value for key, value in payload.items() if key != "prev_hash"}
    entry["content_hash"] = content_hash(entry)
    entry["prev_hash"] = prev
    return entry


def link_entry(entry: dict, previous: dict) -> dict:
    """Return a copy of ``entry`` chained to ``previous``'s content hash."""
    linked = dict(entry)
    linked["prev_hash"] = previous["content_hash"]
    linked["content_hash"] = content_hash(linked)
    return linked


def build_chain(payloads: list[dict]) -> list[dict]:
    """Build a hash chain from payloads, linking each to the previous entry."""
    entries: list[dict] = []
    for payload in payloads:
        entry = build_entry(payload) if not entries else dict(payload)
        if entries:
            entry = link_entry(entry, entries[-1])
        else:
            entry["prev_hash"] = GENESIS_PREV
            entry["content_hash"] = content_hash(entry)
        entries.append(entry)
    return entries


def build_manifest(trajectory_id: str, entries: list[dict]) -> dict:
    """Build a versioned manifest anchoring the chain."""
    manifest = {
        "schema_version": "v1",
        "trajectory_id": trajectory_id,
        "entry_count": len(entries),
        "first_hash": entries[0]["content_hash"] if entries else None,
        "last_hash": entries[-1]["content_hash"] if entries else None,
        "hash_algorithm": HASH_ALGORITHM,
        "canonicalization_version": CANONICAL_VERSION,
    }
    manifest["manifest_hash"] = digest(manifest)
    return manifest


def verify_chain(entries: list[dict], manifest: dict | None = None) -> VerifyResult:
    """Verify chain linkage, content hashes, and (optionally) the manifest."""
    result = VerifyResult(ok=True)

    if not entries:
        result.ok = False
        result.reasons.append("empty chain")
        return result

    if entries[0].get("prev_hash") is not GENESIS_PREV:
        result.ok = False
        result.reasons.append("genesis entry has non-null prev_hash")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or "content_hash" not in entry:
            result.ok = False
            result.reasons.append(f"entry {index} missing content_hash")
            continue
        recomputed = content_hash(entry)
        if recomputed != entry["content_hash"]:
            result.ok = False
            result.reasons.append(f"entry {index} content_hash mismatch")
        if index > 0:
            if entry.get("prev_hash") != entries[index - 1]["content_hash"]:
                result.ok = False
                result.reasons.append(f"entry {index} prev_hash does not link to previous entry")

    if manifest is not None:
        manifest_errors = verify_manifest(manifest, entries)
        if manifest_errors:
            result.ok = False
            result.reasons.extend(manifest_errors)

    return result
def verify_manifest(manifest: dict, entries: list[dict], trajectory_id: str | None = None) -> list[str]:
    """Return manifest inconsistencies (empty when valid)."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest is not an object"]

    if trajectory_id is not None and manifest.get("trajectory_id") != trajectory_id:
        errors.append("trajectory_id mismatch")
    if manifest.get("entry_count") != len(entries):
        errors.append(f"entry_count {manifest.get('entry_count')} != {len(entries)}")
    if manifest.get("first_hash") != (entries[0]["content_hash"] if entries else None):
        errors.append("first_hash mismatch")
    if manifest.get("last_hash") != (entries[-1]["content_hash"] if entries else None):
        errors.append("last_hash mismatch")
    if manifest.get("hash_algorithm") != HASH_ALGORITHM:
        errors.append(f"hash_algorithm {manifest.get('hash_algorithm')} != {HASH_ALGORITHM}")
    if manifest.get("canonicalization_version") != CANONICAL_VERSION:
        errors.append(f"canonicalization_version {manifest.get('canonicalization_version')} != {CANONICAL_VERSION}")

    payload = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != digest(payload):
        errors.append("manifest_hash does not match manifest payload")
    return errors
