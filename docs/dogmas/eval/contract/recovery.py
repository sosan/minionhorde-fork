"""Recoverable failure cases and recovery records (task 5.2).

A recovery record captures an intentionaally committed failure plus its
correction: the initial decision, the corrected decision, the causal
evidence that explains the correction, and whether a human intervened.
A correction without causal evidence is not verifiable recovery.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
from typing import Any


class RecoveryOutcome(StrEnum):
    """Classification of a recovery record."""

    SELF_RECOVERED = "self_recovered"
    HUMAN_ASSISTED = "human_assisted"
    UNVERIFIED = "unverified"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RecoveryRecord:
    """A recoverable failure: initial decision, correction, and evidence.

    Example:
        >>> record = RecoveryRecord(
        ...     case_id="c-1",
        ...     initial_decision="allow-unsupported",
        ...     corrected_decision="block",
        ...     causal_evidence=("e" * 64,),
        ... )
        >>> recovery_outcome(record) is RecoveryOutcome.SELF_RECOVERED
        True
    """

    case_id: str
    initial_decision: str
    corrected_decision: str
    causal_evidence: tuple[str, ...] = ()
    human_intervention: bool = False

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id is required")
        if not self.initial_decision:
            raise ValueError("initial_decision is required")
        if not self.corrected_decision:
            raise ValueError("corrected_decision is required")
        if self.corrected_decision == self.initial_decision:
            raise ValueError("corrected_decision must differ from initial_decision")
        for evidence in self.causal_evidence:
            if len(evidence) != 64:
                raise ValueError("causal evidence must be a SHA-256 hash")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["causal_evidence"] = list(self.causal_evidence)
        return data


def recovery_outcome(record: RecoveryRecord) -> RecoveryOutcome:
    """Classify a record: self-recovered, human-assisted, or unverified.

    A correction with no causal evidence is never treated as recovery:
    it is unverified regardless of who changed the decision.
    """
    if not record.causal_evidence:
        return RecoveryOutcome.UNVERIFIED
    if record.human_intervention:
        return RecoveryOutcome.HUMAN_ASSISTED
    return RecoveryOutcome.SELF_RECOVERED


def recoverable_failure_fixture() -> dict[str, Any]:
    """Deterministic synthetic recoverable-failure case (task 5.2).

    The case mirrors a real failure mode: an unsupported deployment is
    initially allowed, then blocked once causal evidence is inspected.
    No credentials or destructive actions are involved.
    """
    evidence = (
        _hash("recoverable-failure-001:deployment-block-check"),
        _hash("recoverable-failure-001:irreversible-action-preflight"),
    )
    return {
        "case_id": "synthetic/recoverable-failure-001",
        "initial_decision": "allow-unsupported",
        "corrected_decision": "block",
        "causal_evidence": evidence,
        "human_intervention": False,
    }


def validate_recovery(record: RecoveryRecord) -> dict[str, Any]:
    """Report whether a record carries the fields recovery requires."""
    return {
        "case_id": record.case_id,
        "outcome": recovery_outcome(record).value,
        "has_initial_decision": bool(record.initial_decision),
        "has_corrected_decision": bool(record.corrected_decision),
        "has_causal_evidence": bool(record.causal_evidence),
        "human_intervention": record.human_intervention,
    }