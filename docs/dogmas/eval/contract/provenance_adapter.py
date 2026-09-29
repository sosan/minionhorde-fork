"""Adapt manual-ingest results to the versioned evaluation-result contract."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

CONDITION_MAP = {"C0": "base", "C1": "criteria", "C2": "criteria_memory", "C3": "full"}
DIMENSION_BY_CASE = {
    "synthetic/sandbox-postcondition-001": "correction",
    "synthetic/memory-injection-stale-approval-001": "stability",
    "synthetic/approval-expiry-irreversible-001": "stability",
    "synthetic/secret-redaction-001": "stability",
    "synthetic/isolation-downgrade-001": "stability",
    "synthetic/permission-boundary-escalation-001": "stability",
}
ENVIRONMENT_STATUSES = {"provider_error", "timeout", "credential_error", "budget_exceeded", "schema_invalid", "pending", "blocked", "aborted"}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _condition(value: str) -> str:
    if value not in CONDITION_MAP:
        raise ValueError(f"unsupported manual condition: {value}")
    return CONDITION_MAP[value]


def _served_status(requested: str, served: str) -> str:
    if not served or served == "unknown":
        return "unknown"
    if requested and requested != "unknown" and served != requested:
        return "mismatch"
    return "reported"


def _outcome(classification: str) -> str:
    return "model_pass" if classification == "PASS" else "model_fail"


def _dimension(case_id: str) -> dict[str, float | None]:
    dimension = DIMENSION_BY_CASE.get(case_id)
    return {dimension: None} if dimension else {}


def adapt_result(
    manual: dict[str, Any],
    *,
    condition: str,
    response_literal: str | None = None,
    repetition_id: str = "unknown",
    case_language: str = "en",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Convert one manual condition result into an EvaluationResult v1."""
    classification = manual.get("classification", "PARTIAL")
    requested = manual.get("requested_model", "unknown")
    served = manual.get("served_model", "unknown")
    evidence_mode = "literal" if response_literal and response_literal.strip() else "none"
    served_status = _served_status(requested, served)
    sampling = manual.get("sampling", "unknown")
    sampling_parameters = {"raw": sampling, "temperature": "unknown", "other_sampling": "unknown"}
    configuration_mismatch = bool(manual.get("configuration_mismatch", False))
    comparable = served_status == "reported" and sampling != "unknown" and not configuration_mismatch
    explicit_outcome = manual.get("outcome_status")
    outcome_status = explicit_outcome if explicit_outcome in ENVIRONMENT_STATUSES else _outcome(classification)

    return {
        "schema_version": "v1",
        "result_id": _hash(f"{manual.get('case_id')}:{requested}:{repetition_id}:{condition}"),
        "case_id": manual["case_id"],
        "case_version": manual.get("case_version", "v1"),
        "case_hash": _hash(manual["case_id"]),
        "condition": _condition(condition),
        "repetition_id": repetition_id,
        "pair_key": f"{manual['case_id']}:{repetition_id}:{condition}",
        "requested_model": requested,
        "served_model": served,
        "served_model_status": served_status,
        "sampling_parameters": sampling_parameters,
        "case_language": case_language,
        "layer_a_profile": "unknown",
        "layer_b_criteria_version": "unknown",
        "layer_c_memory_version": "unknown",
        "policy_version": "unknown",
        "policy_hash": _hash("unknown-policy"),
        "partition_manifest_hash": _hash("unknown-partition"),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "classification": classification,
        "classification_authority": "rule",
        "outcome_status": outcome_status,
        "evidence_mode": evidence_mode,
        "provenance_status": "limited" if evidence_mode == "literal" else "unverified",
        "comparability": "comparable" if comparable else "non_comparable" if configuration_mismatch else "provisional",
        "discrimination": "unknown",
        "retrieved": {"status": "present" if condition in ("C2", "C3") else "none", "items": 0},
        "dimensions": _dimension(manual["case_id"]),
        "evidence": {
            "reference_hashes": [_hash(response_literal)] if response_literal else [],
            "tool_result_observed": bool(response_literal and ("independent" in response_literal.lower() or "post-operation" in response_literal.lower())),
        },
        "cost": {"input_tokens": None, "output_tokens": None, "model_calls": None},
        "judge": {"judge_id": "rule-classifier", "model_family_relation": False, "agreement_validated": False, "condition_blinded": False},
    }
