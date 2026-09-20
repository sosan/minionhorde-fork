"""Migrate legacy evaluation results into the modern contract.

Implements the legacy-migration contract from the evaluation-provenance spec and
design decision 8: legacy results are imported as `legacy_limited` descriptive
evidence and cannot support causal, transfer, promotion, or Layer C improvement
claims. Legacy dimensions are preserved separately from learning dimensions and
are never silently merged (spec: "Legacy and learning dimensions are not silently
merged").

This module never rewrites the source file: it produces new artifacts that
reference the original.
"""

from __future__ import annotations

from typing import Any

from .canonical import digest

LEGACY_PROVENANCE = "legacy_limited"
LEGACY_AUTHORITY = "unverified"
LEGACY_DIMENSION_PREFIX = "legacy_"

# Fields that carry the same name across both contracts but different semantics.
AMBIGUOUS_DIMENSIONS = {"recovery"}


def is_legacy_result(document: dict) -> bool:
    """Heuristic: a legacy result lacks the modern schema marker and conditions."""
    return "schema_version" not in document and "condition" not in document


def migrate_result(document: dict, *, source_hash: str | None = None) -> dict:
    """Return a modern-shape artifact for a legacy result, limited-provenance.

    The output is intentionally NOT a valid modern `EvaluationResult`: it is a
    migration record that describes the legacy result without granting it modern
    authority. Downstream code must treat it as descriptive only.
    """
    if not is_legacy_result(document):
        raise ValueError("document already uses the modern contract; not a legacy result")

    case_id = str(document.get("case_id", "unknown"))
    model = str(document.get("model", "unknown"))
    provider = str(document.get("provider", "unknown"))
    timestamp = str(document.get("timestamp", ""))
    classification = str(document.get("classification", "UNKNOWN"))

    legacy_dimensions = _migrate_dimensions(document.get("dimensions") or {})

    return {
        "schema_version": "v1",
        "artifact_type": "legacy_migration",
        "provenance_status": LEGACY_PROVENANCE,
        "classification_authority": LEGACY_AUTHORITY,
        "served_model": "unknown",
        "sampling_parameters": "unknown",
        "evidence_mode": "summary",
        "comparability": "non_comparable",
        "case_id": case_id,
        "case_version": "legacy",
        "case_hash": digest({"legacy_case": case_id}),
        "source": {
            "requested_model": model,
            "provider": provider,
            "timestamp": timestamp,
            "classification": classification,
            "source_hash": source_hash,
            "schema_version": "legacy",
        },
        "legacy_dimensions": legacy_dimensions,
        "eligible_claims": {
            "descriptive_report": True,
            "causal": False,
            "transfer": False,
            "promotion": False,
            "layer_c_improvement": False,
        },
    }


def _migrate_dimensions(dimensions: dict) -> dict[str, Any]:
    """Map legacy dimension names into explicitly prefixed names.

    A legacy `recovery` field shares a name with a learning dimension but not its
    semantics, so it is stored as `legacy_recovery` and never merged.
    """
    migrated: dict[str, Any] = {}
    for name, value in dimensions.items():
        if name in AMBIGUOUS_DIMENSIONS:
            migrated[f"{LEGACY_DIMENSION_PREFIX}{name}"] = value
        else:
            migrated[f"{LEGACY_DIMENSION_PREFIX}{name}"] = value
    return migrated


def migration_can_support(artifact: dict, claim: str) -> bool:
    """Return whether a migrated artifact may support the named claim type."""
    return bool(artifact.get("eligible_claims", {}).get(claim, False))
