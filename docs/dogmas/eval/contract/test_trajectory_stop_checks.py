"""Bounded-budget and no-progress stop checks (task 2.4).

The trajectory SHALL abort when consecutive turns in a learning loop produce
no new evidence and no decision change, independently of the existing
maximum-turn budget, and SHALL report the reason. The check is opt-in via
``learning_loop=True`` so bounded Socratic calibration trajectories that do
not enter the learning loop keep their existing behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.trajectory_runtime import Trajectory, TrajectoryError


def test_learning_loop_flag_defaults_to_disabled() -> None:
    trajectory = Trajectory("t-progress")
    assert trajectory.learning_loop is False
    assert trajectory.no_progress_limit == 3
    assert trajectory.no_progress_streak == 0


def test_no_progress_check_is_inactive_without_learning_loop() -> None:
    trajectory = Trajectory("t-calibration")  # learning_loop=False
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")
    trajectory.transition("CHALLENGE", "same")
    trajectory.transition("EVIDENCE_CHECK", "same")
    trajectory.transition("AUDIT", "same")  # would abort if check were active
    assert trajectory.state == "AUDIT"
    assert trajectory.no_progress_streak == 0


def test_three_consecutive_no_progress_turns_abort() -> None:
    trajectory = Trajectory("t-progress", learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")  # evaluates t1: no evidence -> streak 1
    trajectory.transition("CHALLENGE", "same")  # evaluates t2: streak 2
    trajectory.transition("EVIDENCE_CHECK", "same")  # evaluates t3: streak 3 -> abort
    with pytest.raises(TrajectoryError, match="no progress"):
        trajectory.transition("AUDIT", "same")
    assert trajectory.state == "ABORTED"
    assert trajectory.entries[-1].payload["cause"] == "no_progress_exceeded"
    assert trajectory.entries[-1].payload["streak"] == 3


def test_two_no_progress_turns_are_allowed() -> None:
    trajectory = Trajectory("t-progress", learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")  # streak 1
    trajectory.transition("CHALLENGE", "same")  # streak 2
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("evidence-fresh",))
    trajectory.transition("EVIDENCE_CHECK", "progressed")  # new evidence resets streak
    assert trajectory.state == "EVIDENCE_CHECK"
    assert trajectory.no_progress_streak == 0


def test_new_evidence_resets_no_progress_streak() -> None:
    trajectory = Trajectory("t-progress", learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")  # streak 1
    trajectory.transition("CHALLENGE", "same")  # streak 2
    trajectory.transition("EVIDENCE_CHECK", "same")  # streak 3 (still under limit)
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("evidence-1",))
    trajectory.transition("AUDIT", "new evidence")  # new evidence resets streak
    assert trajectory.no_progress_streak == 0
    assert trajectory.state == "AUDIT"


def test_new_changed_claim_resets_no_progress_streak() -> None:
    trajectory = Trajectory("t-progress", learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")  # streak 1
    trajectory.transition("CHALLENGE", "same")  # streak 2
    trajectory.transition("EVIDENCE_CHECK", "same")  # streak 3
    trajectory.amend_turn(trajectory._turns[-1].turn_id, changed_claims=("claim-revised",))
    trajectory.transition("AUDIT", "decision changed")  # new claim resets streak
    assert trajectory.no_progress_streak == 0


def test_repeating_same_evidence_does_not_count_as_progress() -> None:
    trajectory = Trajectory("t-progress", learning_loop=True)
    trajectory.transition("INTERPRET", "start")
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("evidence-1",))
    trajectory.transition("REFORMULATE", "first pass")  # new evidence -> streak 0
    assert trajectory.no_progress_streak == 0
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("evidence-1",))
    trajectory.transition("CHALLENGE", "repeat")  # same evidence -> streak 1
    assert trajectory.no_progress_streak == 1


def test_custom_no_progress_limit() -> None:
    trajectory = Trajectory("t-progress", no_progress_limit=1, learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")  # streak 1 -> abort at next transition
    with pytest.raises(TrajectoryError, match="no progress"):
        trajectory.transition("CHALLENGE", "same")
    assert trajectory.state == "ABORTED"


def test_max_turns_budget_still_enforced() -> None:
    trajectory = Trajectory("t-budget", max_turns=3, learning_loop=True)
    trajectory.transition("INTERPRET", "start")
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("e1",))
    trajectory.transition("REFORMULATE", "1")
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("e2",))
    trajectory.transition("CHALLENGE", "2")
    trajectory.amend_turn(trajectory._turns[-1].turn_id, evidence_refs=("e3",))
    with pytest.raises(TrajectoryError, match="maximum turn budget"):
        trajectory.transition("EVIDENCE_CHECK", "3")
    assert trajectory.state == "ABORTED"
    assert trajectory.entries[-1].payload["cause"] == "max_turns_exceeded"


def test_progress_and_turn_budget_are_independent() -> None:
    trajectory = Trajectory("t-both", max_turns=5, no_progress_limit=2, learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")  # streak 1
    trajectory.transition("CHALLENGE", "same")  # streak 2
    with pytest.raises(TrajectoryError, match="no progress"):
        trajectory.transition("EVIDENCE_CHECK", "same")  # would exceed -> abort before budget
    assert trajectory.state == "ABORTED"
    assert trajectory.entries[-1].payload["cause"] == "no_progress_exceeded"


def test_no_progress_abort_is_append_only_and_chain_verifiable() -> None:
    trajectory = Trajectory("t-chain", learning_loop=True)
    trajectory.transition("INTERPRET", "same")
    trajectory.transition("REFORMULATE", "same")
    trajectory.transition("CHALLENGE", "same")
    trajectory.transition("EVIDENCE_CHECK", "same")
    try:
        trajectory.transition("AUDIT", "same")
    except TrajectoryError:
        pass
    ok, reasons = trajectory.verify_chain()
    assert ok, reasons
    assert trajectory.entries[-1].entry_type == "state"