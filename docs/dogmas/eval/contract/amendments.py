"""Structured Layer C → Layer B amendment proposals (task 10.14).

An amendment proposal records the current criterion, contradicting
evidence, proposed text, and the precedences the change would affect. It
MUST be human-approved, MUST be re-run through the regression suite
before it can be treated as stable, and MAY NOT self-apply: a stable
amendment is the only state from which a new Layer B profile may be
derived.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .layer_profiles import LayerBProfile


class AmendmentStatus(str, Enum):
    PROPOSED = "proposed"
    HUMAN_APPROVED = "human_approved"
    REGRESSION_PENDING = "regression_pending"
    STABLE = "stable"
    REJECTED = "rejected"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: str) -> str:
    from .canonical import digest

    return digest(value)


def propose_amendment(
    *,
    proposal_id: str,
    rule_id: str,
    current_version: str,
    current_text: str,
    contradicting_evidence: tuple[str, ...],
    proposed_text: str,
    precedence_change: bool,
    affected_precedences: tuple[str, ...],
) -> dict[str, Any]:
    """Create a new amendment proposal in ``PROPOSED`` state."""
    return {
        "proposal_id": proposal_id,
        "status": AmendmentStatus.PROPOSED.value,
        "rule_id": rule_id,
        "current_version": current_version,
        "current_text": current_text,
        "proposed_text": proposed_text,
        "precedence_change": precedence_change,
        "affected_precedences": tuple(affected_precedences),
        "contradicting_evidence": tuple(contradicting_evidence),
        "proposed_at": _utcnow(),
        "proposal_hash": _hash(f"proposal:{proposal_id}:{rule_id}:{current_version}"),
        "applied": False,
    }


def approve_human(record: dict[str, Any], *, reviewer_id: str, rationale_hash: str) -> dict[str, Any]:
    """Promote a proposal to ``HUMAN_APPROVED``; never auto-approved."""
    if record["status"] != AmendmentStatus.PROPOSED.value:
        raise RuntimeError(f"cannot human-approve amendment in state {record['status']!r}")
    record["status"] = AmendmentStatus.HUMAN_APPROVED.value
    record["human_reviewer_id"] = reviewer_id
    record["human_rationale_hash"] = rationale_hash
    record["human_approved_at"] = _utcnow()
    return record


def mark_regression_rerun(record: dict[str, Any], *, rerun_manifest_hash: str) -> dict[str, Any]:
    """Mark the regression re-run in progress; status becomes ``REGRESSION_PENDING``."""
    if record["status"] != AmendmentStatus.HUMAN_APPROVED.value:
        raise RuntimeError(
            f"cannot start regression re-run from state {record['status']!r}; "
            "human approval required first"
        )
    record["status"] = AmendmentStatus.REGRESSION_PENDING.value
    record["regression_rerun_manifest"] = rerun_manifest_hash
    record["regression_rerun_at"] = _utcnow()
    return record


def mark_stable(record: dict[str, Any], *, regression_passed: bool) -> dict[str, Any]:
    """Finalize after a regression re-run.

    ``regression_passed=True`` promotes the amendment to ``STABLE``;
    a failed regression drops it to ``REJECTED``. The amendment stays
    an inert record in either case.
    """
    if record["status"] != AmendmentStatus.REGRESSION_PENDING.value:
        raise RuntimeError(
            f"cannot mark stable from state {record['status']!r}; regression re-run required"
        )
    record["regression_passed"] = regression_passed
    if regression_passed:
        record["status"] = AmendmentStatus.STABLE.value
        record["stabilized_at"] = _utcnow()
    else:
        record["status"] = AmendmentStatus.REJECTED.value
        record["rejected_reason"] = "regression_re_run_failed"
        record["rejected_at"] = _utcnow()
    return record


def reject(record: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Reject a proposal (or a regression-pending record) directly."""
    if record["status"] in (AmendmentStatus.STABLE.value, AmendmentStatus.REJECTED.value):
        raise RuntimeError(f"cannot reject amendment in terminal state {record['status']!r}")
    record["status"] = AmendmentStatus.REJECTED.value
    record["rejected_reason"] = reason
    record["rejected_at"] = _utcnow()
    return record


def apply_if_stable(record: dict[str, Any], layer_b: LayerBProfile) -> LayerBProfile:
    """Produce a new ``LayerBProfile`` only from a ``STABLE`` amendment.

    Refuses to return anything for proposals that have not been human
    approved, that have not been re-run through the regression suite, or
    that failed that re-run. The original ``layer_b`` profile is never
    mutated; ``LayerBProfile`` is frozen, so we use ``dataclasses.replace``
    to build the updated copy.
    """
    status = record["status"]
    if status == AmendmentStatus.PROPOSED.value:
        raise RuntimeError("amendment requires human approval before any apply")
    if status in (AmendmentStatus.HUMAN_APPROVED.value, AmendmentStatus.REGRESSION_PENDING.value):
        raise RuntimeError("amendment requires regression re-run before any apply")
    if status == AmendmentStatus.REJECTED.value:
        raise RuntimeError("amendment is not stable; rejected amendments cannot apply")
    if status != AmendmentStatus.STABLE.value:
        raise RuntimeError(f"amendment is not stable (state={status!r})")
    record["applied"] = True
    record["applied_at"] = _utcnow()
    # The amendment updates the rule referenced by ``rule_id``. A real
    # deployment would replace the matching criterion; for the contract
    # surface we return a copy of the profile so the caller can persist a
    # new profile hash. The previous profile is untouched.
    return dataclasses.replace(layer_b)
