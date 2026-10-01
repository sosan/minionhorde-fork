"""Actors, human review, dissent, and evidence-dependent invalidation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

ACTOR_ROLES = ("producer", "classifier", "custodian", "reviewer")
REVIEW_STATES = ("OPEN", "ESCALATED", "CLOSED", "SUPERSEDED")
INDEPENDENCE = ("independent", "dependent", "unknown")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Actor:
    actor_id: str
    role: str
    model_family: str | None = None
    independence: str = "unknown"

    def __post_init__(self) -> None:
        if self.role not in ACTOR_ROLES:
            raise ValueError(f"unsupported actor role: {self.role}")
        if self.independence not in INDEPENDENCE:
            raise ValueError(f"unsupported independence: {self.independence}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HumanReview:
    review_id: str
    reviewer: Actor
    state: str = "OPEN"
    decision: str | None = None
    rationale_hash: str | None = None
    evidence_blinded: bool = False
    dissent: bool = False
    dissent_reason: str | None = None
    created_at: str = field(default_factory=_now)
    closed_at: str | None = None
    supersedes_review_id: str | None = None

    def __post_init__(self) -> None:
        if self.reviewer.role != "reviewer":
            raise ValueError("human review requires an actor with reviewer role")
        if self.state not in REVIEW_STATES:
            raise ValueError(f"unsupported review state: {self.state}")

    def close(self, decision: str, rationale_hash: str, *, dissent: bool = False, dissent_reason: str | None = None) -> None:
        if self.state not in {"OPEN", "ESCALATED"}:
            raise ValueError(f"cannot close review in state {self.state}")
        self.state = "CLOSED"
        self.decision = decision
        self.rationale_hash = rationale_hash
        self.dissent = dissent
        self.dissent_reason = dissent_reason
        self.closed_at = _now()

    def escalate(self, reason: str) -> None:
        if self.state != "OPEN":
            raise ValueError(f"cannot escalate review in state {self.state}")
        self.state = "ESCALATED"
        self.dissent = True
        self.dissent_reason = reason

    def supersede(self, replacement_review_id: str) -> None:
        if self.state != "CLOSED":
            raise ValueError(f"cannot supersede review in state {self.state}")
        self.state = "SUPERSEDED"
        self.supersedes_review_id = replacement_review_id

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reviewer"] = self.reviewer.to_dict()
        return result


def apply_custody_resolution(result: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
    """Return a result downgraded when its evidence is expired or corrupted."""
    updated = dict(result)
    state = resolution.get("state")
    if state == "CORRUPTED":
        updated["evaluation_validity"] = "invalidated"
        updated["provenance_status"] = "unverified"
        updated["comparability"] = "non_comparable"
        updated["classification_authority"] = "unverified"
        updated["invalidation_reason"] = "evidence custody is CORRUPTED"
    elif resolution.get("literal_expired"):
        updated["evaluation_validity"] = "limited"
        updated["evidence_mode"] = "hash_only"
        updated["provenance_status"] = "limited"
        updated["invalidation_reason"] = "stored literal expired; hash-only evidence retained"
    else:
        updated.setdefault("evaluation_validity", "valid")
    return updated
