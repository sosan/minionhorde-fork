"""Task 5.3: run prior passing cases after a trajectory or memory candidate
change and fail the candidate on regression."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from regression import RegressionCandidate, evaluate_regression


PASSING = [
    {"case_id": "c-1", "case_version": "v1", "passed": True},
    {"case_id": "c-2", "case_version": "v1", "passed": True},
    {"case_id": "c-3", "case_version": "v1", "passed": True},
]


def test_no_regression_keeps_candidate_passing() -> None:
    candidate = RegressionCandidate(candidate_id="cand-1", prior_passing_cases=tuple(PASSING))
    reruns = {"c-1": [True, True], "c-2": [True, True], "c-3": [True, True]}
    report = evaluate_regression(candidate, reruns)
    assert report["candidate_status"] == "passing"
    assert report["confirmed_regressions"] == []


def test_single_flip_is_unconfirmed_without_confirmation_runs() -> None:
    candidate = RegressionCandidate(candidate_id="cand-1", prior_passing_cases=tuple(PASSING))
    reruns = {"c-1": [False, True], "c-2": [True, True], "c-3": [True, True]}
    report = evaluate_regression(candidate, reruns)
    assert report["candidate_status"] == "pending"
    assert report["unconfirmed_flips"] == ["c-1"]


def test_confirmed_flip_fails_candidate() -> None:
    candidate = RegressionCandidate(candidate_id="cand-1", prior_passing_cases=tuple(PASSING))
    reruns = {"c-1": [False, False], "c-2": [True, True], "c-3": [True, True]}
    report = evaluate_regression(candidate, reruns)
    assert report["candidate_status"] == "failed"
    assert report["confirmed_regressions"] == ["c-1"]


def test_regression_considers_prior_passing_cases_only() -> None:
    candidate = RegressionCandidate(
        candidate_id="cand-1",
        prior_passing_cases=(
            {"case_id": "c-1", "case_version": "v1", "passed": True},
            {"case_id": "c-2", "case_version": "v1", "passed": False},
        ),
    )
    reruns = {"c-1": [False, False], "c-2": [True, True]}
    report = evaluate_regression(candidate, reruns)
    # c-2 was already failing before the change; it is not a regression.
    assert report["checked_cases"] == ["c-1"]
    assert report["confirmed_regressions"] == ["c-1"]


def test_case_not_rerun_is_not_counted_as_regression() -> None:
    candidate = RegressionCandidate(candidate_id="cand-1", prior_passing_cases=tuple(PASSING))
    reruns = {"c-1": [True, True]}
    report = evaluate_regression(candidate, reruns)
    assert report["checked_cases"] == ["c-1"]
    assert report["unchecked_cases"] == ["c-2", "c-3"]
    assert report["candidate_status"] == "pending"


def test_missing_rerun_case_raises() -> None:
    candidate = RegressionCandidate(candidate_id="cand-1", prior_passing_cases=tuple(PASSING))
    with pytest.raises(KeyError, match="c-1"):
        evaluate_regression(candidate, {"c-9": [True]})


def test_custom_confirmation_runs_are_respected() -> None:
    candidate = RegressionCandidate(candidate_id="cand-1", prior_passing_cases=tuple(PASSING))
    reruns = {"c-1": [False, False, False, True], "c-2": [True], "c-3": [True]}
    report = evaluate_regression(candidate, reruns, confirmations_required=3)
    # 3 failures out of 4 runs confirm at threshold 3.
    assert report["confirmed_regressions"] == ["c-1"]
    assert report["candidate_status"] == "failed"