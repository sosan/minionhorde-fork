"""Regression checks for trajectory or memory candidate changes (task 5.3).

When a candidate learning change is proposed, the cases that passed before
the change must still pass after it. A single failed rerun is not a
regression: failures are confirmed through repetition (via
``confirm_regression_failures``), and only confirmed regressions fail the
candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trajectory_runtime import confirm_regression_failures


@dataclass(frozen=True)
class RegressionCandidate:
    """A trajectory/memory change candidate being evaluated for regression."""

    candidate_id: str
    prior_passing_cases: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id is required")


def evaluate_regression(
    candidate: RegressionCandidate,
    reruns: Mapping[str, list[bool]],
    confirmations_required: int = 2,
) -> dict[str, Any]:
    """Re-run prior passing cases after the candidate change.

    ``reruns`` maps case_id to the outcome of each repeat run (True = still
    passing). Cases that already failed before the change are not part of
    the regression check; only prior-passing cases count.
    """
    prior_ids = {case["case_id"] for case in candidate.prior_passing_cases}
    unknown = sorted(set(reruns) - prior_ids)
    if unknown:
        expected = ", ".join(sorted(prior_ids))
        raise KeyError(f"rerun case(s) '{', '.join(unknown)}' are not prior cases; expected among: {expected}")

    passing_ids = {case["case_id"] for case in candidate.prior_passing_cases if case["passed"]}
    checked: list[str] = []
    checked_outcomes: dict[str, list[bool]] = {}
    for case in candidate.prior_passing_cases:
        if case["passed"] and case["case_id"] in reruns:
            checked.append(case["case_id"])
            checked_outcomes[case["case_id"]] = reruns[case["case_id"]]

    confirmed: list[str] = []
    unconfirmed_flips: list[str] = []
    for case_id in checked:
        report = confirm_regression_failures(checked_outcomes[case_id], confirmations_required)
        if report["confirmed"]:
            confirmed.append(case_id)
        elif any(not outcome for outcome in checked_outcomes[case_id]):
            unconfirmed_flips.append(case_id)

    unchecked = sorted(passing_ids - set(checked))
    if confirmed:
        status = "failed"
    elif unconfirmed_flips or unchecked:
        status = "pending"
    else:
        status = "passing"
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_status": status,
        "checked_cases": checked,
        "unchecked_cases": unchecked,
        "confirmed_regressions": confirmed,
        "unconfirmed_flips": unconfirmed_flips,
        "confirmations_required": confirmations_required,
    }