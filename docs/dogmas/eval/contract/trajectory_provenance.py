"""Integration of Socratic trajectories with custody, actors, and human review."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    from .evidence_custody import EvidenceCustody, resolve_custody
    from .review import Actor, HumanReview
    from .trajectory_runtime import Trajectory, TrajectoryError
except ImportError:  # direct test/module execution
    from evidence_custody import EvidenceCustody, resolve_custody
    from review import Actor, HumanReview
    from trajectory_runtime import Trajectory, TrajectoryError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TrajectoryProvenance:
    """Binds a Trajectory to its EvidenceCustody, actors, and human reviews."""

    trajectory: Trajectory
    custody: EvidenceCustody
    actors: dict[str, Actor] = field(default_factory=dict)
    reviews: list[HumanReview] = field(default_factory=list)
    custody_id: str = ""
    custody_state: str = "OPEN"
    evaluation_validity: str = "valid"
    invalidation_reason: str = ""
    evidence_mode: str = "literal"
    provenance_status: str = "verified"

    def __post_init__(self) -> None:
        if not self.custody_id:
            self.custody_id = self.custody.custody_id
        self.custody_state = self.custody.state

    def register_actor(self, actor: Actor) -> None:
        if actor.role in self.actors:
            raise TrajectoryError(f"actor role '{actor.role}' already registered")
        self.actors[actor.role] = actor

    def add_review(self, review: HumanReview) -> None:
        self.reviews.append(review)

    def resolve_and_invalidate(self) -> dict[str, Any]:
        """Resolve custody and invalidate trajectory if corrupted or expired."""
        resolution = resolve_custody(self.custody)
        self.custody_state = resolution["state"]
        self.evidence_mode = resolution["evidence_mode"]
        self.provenance_status = resolution["provenance_status"]

        if resolution["state"] == "CORRUPTED":
            self.evaluation_validity = "invalidated"
            self.invalidation_reason = "evidence custody is CORRUPTED"
        elif resolution.get("literal_expired"):
            self.evaluation_validity = "limited"
            self.invalidation_reason = "stored literal expired; hash-only evidence retained"
        else:
            self.evaluation_validity = "valid"
            self.invalidation_reason = ""

        return resolution

    def snapshot(self) -> dict[str, Any]:
        """Return a provenance snapshot including custody, actors, and reviews."""
        return {
            "trajectory_id": self.trajectory.trajectory_id,
            "state": self.trajectory.state,
            "custody_id": self.custody_id,
            "custody_state": self.custody_state,
            "evaluation_validity": self.evaluation_validity,
            "invalidation_reason": self.invalidation_reason,
            "evidence_mode": self.evidence_mode,
            "provenance_status": self.provenance_status,
            "actors": {role: actor.to_dict() for role, actor in self.actors.items()},
            "reviews": [review.to_dict() for review in self.reviews],
            "trajectory_snapshot": self.trajectory.snapshot(),
        }


def validate_trajectory_snapshot(snapshot: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a trajectory snapshot against required fields."""
    required = ["trajectory_id", "state", "custody_id", "custody_state", "evaluation_validity"]
    missing = [field for field in required if field not in snapshot]
    return not missing, missing


def apply_custody_to_trajectory(provenance: TrajectoryProvenance) -> dict[str, Any]:
    """Return a trajectory record with custody metadata applied."""
    provenance.resolve_and_invalidate()
    snapshot = provenance.snapshot()
    valid, missing = validate_trajectory_snapshot(snapshot)
    if not valid:
        raise TrajectoryError(f"snapshot missing required fields: {missing}")
    return snapshot


def validate_against_schema(
    snapshot: dict[str, Any],
    schema_path: str = "docs/dogmas/eval/schemas/v1/trajectory.schema.json",
) -> tuple[bool, list[str]]:
    """Validate a trajectory snapshot against the JSON schema."""
    import json
    from pathlib import Path

    try:
        from jsonschema import validate, ValidationError, Draft202012Validator
    except ImportError:
        return False, ["jsonschema package not installed"]

    schema_file = Path(schema_path)
    if not schema_file.exists():
        return False, [f"schema file not found: {schema_path}"]

    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(snapshot))
    if errors:
        messages = [f"{err.json_path}: {err.message}" for err in errors]
        return False, messages
    return True, []
