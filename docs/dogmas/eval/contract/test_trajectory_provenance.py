from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from trajectory_provenance import TrajectoryProvenance, validate_trajectory_snapshot, apply_custody_to_trajectory
from trajectory_runtime import Trajectory
from evidence_custody import create_custody
from review import Actor, HumanReview


def test_link_trajectory_with_custody(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("test case", encoding="utf-8")
    custody = create_custody("custody-1", {"case": artifact})
    trajectory = Trajectory("traj-1")
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    assert provenance.custody_id == "custody-1"
    assert provenance.custody_state == "OPEN"
    assert provenance.evaluation_validity == "valid"


def test_register_actors() -> None:
    trajectory = Trajectory("traj-2")
    custody = create_custody("custody-2", {})
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    producer = Actor(actor_id="p1", role="producer", independence="independent")
    provenance.register_actor(producer)
    assert "producer" in provenance.actors
    with pytest.raises(Exception, match="already registered"):
        provenance.register_actor(producer)


def test_add_human_review() -> None:
    trajectory = Trajectory("traj-3")
    custody = create_custody("custody-3", {})
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    review = HumanReview(review_id="rev-1", reviewer=reviewer)
    provenance.add_review(review)
    assert len(provenance.reviews) == 1


def test_resolve_valid_custody(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("test case", encoding="utf-8")
    custody = create_custody("custody-4", {"case": artifact})
    trajectory = Trajectory("traj-4")
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    resolution = provenance.resolve_and_invalidate()
    assert resolution["state"] == "OPEN"
    assert provenance.evaluation_validity == "valid"
    assert provenance.evidence_mode == "literal"


def test_invalidate_on_corruption(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("test case", encoding="utf-8")
    custody = create_custody("custody-5", {"case": artifact})
    trajectory = Trajectory("traj-5")
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    # Corrupt the artifact
    artifact.write_text("modified", encoding="utf-8")
    resolution = provenance.resolve_and_invalidate()
    assert resolution["state"] == "CORRUPTED"
    assert provenance.evaluation_validity == "invalidated"
    assert "CORRUPTED" in provenance.invalidation_reason


def test_degrade_on_literal_expiry() -> None:
    from datetime import datetime, timedelta, timezone
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    custody = create_custody("custody-6", {}, literal_response="test", literal_expires_at=expired)
    trajectory = Trajectory("traj-6")
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    resolution = provenance.resolve_and_invalidate()
    assert resolution["literal_expired"] is True
    assert provenance.evaluation_validity == "limited"
    assert provenance.evidence_mode == "hash_only"


def test_snapshot_includes_all_components() -> None:
    trajectory = Trajectory("traj-7")
    trajectory.transition("INTERPRET", "case_loaded")
    custody = create_custody("custody-7", {})
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    producer = Actor(actor_id="p1", role="producer", independence="independent")
    provenance.register_actor(producer)
    reviewer = Actor(actor_id="r1", role="reviewer", independence="independent")
    review = HumanReview(review_id="rev-1", reviewer=reviewer)
    provenance.add_review(review)
    snapshot = provenance.snapshot()
    assert snapshot["trajectory_id"] == "traj-7"
    assert "producer" in snapshot["actors"]
    assert len(snapshot["reviews"]) == 1
    assert "trajectory_snapshot" in snapshot


def test_validate_trajectory_snapshot() -> None:
    valid_snapshot = {
        "trajectory_id": "traj-1",
        "state": "COMPLETED",
        "custody_id": "custody-1",
        "custody_state": "OPEN",
        "evaluation_validity": "valid",
    }
    valid, missing = validate_trajectory_snapshot(valid_snapshot)
    assert valid
    invalid_snapshot = {"trajectory_id": "traj-2"}
    valid, missing = validate_trajectory_snapshot(invalid_snapshot)
    assert not valid
    assert "state" in missing


def test_apply_custody_to_trajectory(tmp_path: Path) -> None:
    artifact = tmp_path / "case.txt"
    artifact.write_text("test case", encoding="utf-8")
    custody = create_custody("custody-8", {"case": artifact})
    trajectory = Trajectory("traj-8")
    trajectory.transition("INTERPRET", "case_loaded")
    provenance = TrajectoryProvenance(trajectory=trajectory, custody=custody)
    record = apply_custody_to_trajectory(provenance)
    assert record["trajectory_id"] == "traj-8"
    assert record["custody_id"] == "custody-8"
    assert record["evaluation_validity"] == "valid"
