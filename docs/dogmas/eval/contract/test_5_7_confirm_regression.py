"""Task 5.7: confirmed regression failures (edge coverage).

A regression SHALL be declared only when the failure is reproduced across
the configured confirmation re-runs; single-run flips are recorded as
unconfirmed and never fail a candidate by themselves.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from trajectory_runtime import confirm_regression_failures


def test_default_confirmations_required_is_two() -> None:
    assert confirm_regression_failures([False, False])["confirmed"]
    assert not confirm_regression_failures([False])["confirmed"]


def test_empty_outcomes_are_unconfirmed() -> None:
    result = confirm_regression_failures([])
    assert not result["confirmed"]
    assert result["status"] == "unconfirmed"
    assert result["runs"] == 0
    assert result["failures"] == 0


def test_single_flip_is_unconfirmed() -> None:
    result = confirm_regression_failures([False, True, True])
    assert not result["confirmed"]
    assert result["status"] == "unconfirmed"
    assert result["failures"] == 1
    assert result["runs"] == 3


def test_failure_reproduced_across_confirmation_runs_confirms() -> None:
    result = confirm_regression_failures([False, False, True])
    assert result["confirmed"]
    assert result["status"] == "confirmed"
    assert result["failures"] == 2


def test_threshold_three_needs_three_reproduced_failures() -> None:
    confirmed = confirm_regression_failures([False, False, False, True], confirmations_required=3)
    assert confirmed["confirmed"]
    assert confirmed["failures"] == 3
    unconfirmed = confirm_regression_failures([False, False, True, True], confirmations_required=3)
    assert not unconfirmed["confirmed"]
    assert unconfirmed["failures"] == 2


def test_threshold_is_not_met_by_insufficient_runs() -> None:
    # Two failing runs cannot confirm a threshold of three regardless of value.
    result = confirm_regression_failures([False, False], confirmations_required=3)
    assert not result["confirmed"]
    assert result["runs"] == 2


def test_single_confirmation_threshold_confirms_one_failure() -> None:
    result = confirm_regression_failures([False], confirmations_required=1)
    assert result["confirmed"]
    assert result["status"] == "confirmed"


def test_all_pass_is_unconfirmed() -> None:
    result = confirm_regression_failures([True, True, True])
    assert not result["confirmed"]
    assert result["failures"] == 0


def test_all_fail_confirms() -> None:
    result = confirm_regression_failures([False, False, False])
    assert result["confirmed"]
    assert result["runs"] == 3


def test_returns_run_and_failure_counts() -> None:
    result = confirm_regression_failures([True, False, False, True, False])
    assert result["runs"] == 5
    assert result["failures"] == 3
    assert result["confirmed"]