from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from trajectory_runtime import Trajectory, TrajectoryError, detect_non_minimal_correction, confirm_regression_failures

def test_trajectory_lifecycle() -> None:
    trajectory = Trajectory("traj-1", max_turns=8)
    assert trajectory.state == "INIT"
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "socratic_challenge")
    trajectory.transition("EVIDENCE_CHECK", "evidence_retrieved")
    trajectory.transition("CORRECT", "correction_applied")
    trajectory.transition("AUDIT", "audit_started")
    trajectory.complete()
    assert trajectory.state == "COMPLETED"
    assert len(trajectory.turns) == 6


def test_invalid_transition_raises() -> None:
    trajectory = Trajectory("traj-2")
    trajectory.transition("INTERPRET", "case_loaded")
    with pytest.raises(TrajectoryError, match="invalid transition"):
        trajectory.transition("CORRECT", "skip")


def test_terminal_state_prevents_transition() -> None:
    trajectory = Trajectory("traj-3")
    trajectory.complete()
    with pytest.raises(TrajectoryError, match="terminal"):
        trajectory.transition("INTERPRET", "retry")


def test_max_turns_budget() -> None:
    trajectory = Trajectory("traj-4", max_turns=2)
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "challenge")
    with pytest.raises(TrajectoryError, match="maximum turn budget"):
        trajectory.transition("EVIDENCE_CHECK", "evidence")
    assert trajectory.state == "ABORTED"


def test_hash_chain_integrity() -> None:
    trajectory = Trajectory("traj-5")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "challenge")
    trajectory.transition("EVIDENCE_CHECK", "evidence")
    trajectory.complete()
    valid, reasons = trajectory.verify_chain()
    assert valid, reasons


def test_hash_chain_detects_mutation() -> None:
    trajectory = Trajectory("traj-6")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "challenge")
    trajectory.complete()
    # Simulate mutation by modifying payload
    trajectory._entries[0].payload["state"] = "MUTATED"
    valid, reasons = trajectory.verify_chain()
    assert not valid
    assert any("hash mismatch" in reason for reason in reasons)


def test_append_only_enforcement() -> None:
    trajectory = Trajectory("traj-7")
    trajectory.transition("INTERPRET", "case_loaded")
    initial_entries = len(trajectory.entries)
    trajectory.transition("CHALLENGE", "challenge")
    assert len(trajectory.entries) == initial_entries + 1
    # Entries list is append-only; no removal allowed
    assert trajectory.entries[0].sequence == 0


def test_amend_turn_only_current() -> None:
    trajectory = Trajectory("traj-8")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.transition("CHALLENGE", "challenge")
    current_turn_id = trajectory.turns[-1].turn_id
    trajectory.amend_turn(current_turn_id, challenges=("challenge-1",))
    assert trajectory.turns[-1].challenges == ("challenge-1",)
    # Cannot amend previous turn
    with pytest.raises(TrajectoryError, match="current turn"):
        trajectory.amend_turn(trajectory.turns[0].turn_id, challenges=("old",))


def test_interrupt_terminal() -> None:
    trajectory = Trajectory("traj-9")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.interrupt("timeout")
    assert trajectory.state == "INTERRUPTED"
    with pytest.raises(TrajectoryError, match="terminal"):
        trajectory.interrupt("retry")


def test_snapshot_includes_chain() -> None:
    trajectory = Trajectory("traj-10")
    trajectory.transition("INTERPRET", "case_loaded")
    trajectory.complete()
    snapshot = trajectory.snapshot()
    assert snapshot["trajectory_id"] == "traj-10"
    assert snapshot["state"] == "COMPLETED"
    assert len(snapshot["entries"]) > 0
    assert len(snapshot["turns"]) > 0


def test_detect_non_minimal_correction() -> None:
    before = {"feature_enabled": False, "version": 3, "metadata": "old"}
    after = {"feature_enabled": True, "version": 3, "metadata": "new"}
    result = detect_non_minimal_correction(before, after, allowed_fields={"feature_enabled"})
    assert not result["minimal"]
    assert "metadata" in result["extra_fields"]


def test_detect_minimal_correction() -> None:
    before = {"feature_enabled": False, "version": 3}
    after = {"feature_enabled": True, "version": 3}
    result = detect_non_minimal_correction(before, after, allowed_fields={"feature_enabled"})
    assert result["minimal"]
    assert result["extra_fields"] == []


def test_confirm_regression_failures() -> None:
    outcomes = [False, False, True]
    result = confirm_regression_failures(outcomes, confirmations_required=2)
    assert result["confirmed"]
    assert result["failures"] == 2


def test_unconfirmed_regression() -> None:
    outcomes = [False, True, True]
    result = confirm_regression_failures(outcomes, confirmations_required=2)
    assert not result["confirmed"]
    assert result["status"] == "unconfirmed"
