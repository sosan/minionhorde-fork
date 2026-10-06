"""Versioned readers and schema migration artifacts (task 10.27).

A ``VersionedReader`` looks up a registered reader for the schema
version a document claims; unknown versions are rejected. ``migrate_artifact``
never rewrites the original in place — it produces a separately hashed
artifact whose ``lossy_semantics`` list names the dimensions whose
meaning changed during migration. ``downgrade_claims`` consumes that
list to reduce the artifact's eligible claim scope.
"""

from __future__ import annotations

from typing import Any, Callable

from .canonical import digest


class VersionedReader:
    """A registry of version-aware readers for evaluation artifacts."""

    def __init__(self) -> None:
        self._readers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def register(self, version: str, reader: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._readers[version] = reader

    def read(self, version: str, document: dict[str, Any]) -> dict[str, Any]:
        try:
            reader = self._readers[version]
        except KeyError:
            raise KeyError(f"unknown schema version: {version!r}; no reader registered") from None
        return reader(document)


def migrate_artifact(
    original: dict[str, Any],
    *,
    from_version: str,
    to_version: str,
    lossy_semantics: list[str] | None = None,
) -> dict[str, Any]:
    """Produce a separately hashed migration artifact.

    ``original`` is never mutated. The returned artifact carries both the
    source hash (over the original document) and a migration hash
    (over the new artifact body, excluding the ``migration_hash`` field
    itself). ``lossy_semantics`` lists the dimension names whose meaning
    changed during migration; downstream claim evaluation uses them.
    """
    lossy = list(lossy_semantics or [])
    body: dict[str, Any] = {
        "schema_version": to_version,
        "source_version": from_version,
        "target_version": to_version,
        "case_id": original.get("case_id", ""),
        "lossy_semantics": lossy,
    }
    for key, value in original.items():
        if key in body or key == "schema_version" or key == "case_id":
            continue
        body[key] = value
    source_hash = digest(original)
    artifact = dict(body)
    artifact["source_hash"] = source_hash
    artifact["migration_hash"] = digest(
        {key: value for key, value in artifact.items() if key != "migration_hash"}
    )
    return artifact


_BASE_ELIGIBLE: dict[str, bool] = {
    "descriptive_report": True,
    "causal": False,
    "transfer": False,
    "promotion": False,
    "layer_c_improvement": False,
}


def downgrade_claims(artifact: dict[str, Any]) -> dict[str, Any]:
    """Reduce an artifact's eligible claim scope based on migration losses.

    Every migrated artifact is treated as non-comparable (its provenance
    chain does not match native v1 records). Artifacts whose migration
    lost semantic meaning are additionally marked limited/summary so
    downstream reporting must not over-claim.
    """
    lossy = list(artifact.get("lossy_semantics") or [])
    result: dict[str, Any] = {
        "eligible_claims": dict(_BASE_ELIGIBLE),
        "comparability": "non_comparable",
        "downgraded": lossy,
    }
    if lossy:
        result["provenance_status"] = "limited"
        result["evidence_mode"] = "summary"
    else:
        result["provenance_status"] = "full"
        result["evidence_mode"] = "full"
    return result
