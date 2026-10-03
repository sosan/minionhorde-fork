"""Task 5.4: metrics for comprehension, correction, transfer, recovery,
stability, regression, human intervention, and token/turn cost."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from metrics import compute_learning_metrics


def _result(
    *,
    dimensions: dict,
    cost: dict | None = None,
    regression: dict | None = None,
    human_intervention: bool = False,
) -> dict:
    return {
        "result_id": "r",
        "case_id": "c",
        "condition": "full",
        "dimensions": dimensions,
        "cost": cost or {"input_tokens": 20, "output_tokens": 10, "model_calls": 1, "turns": 2},
        "regression": regression,
        "human_intervention": human_intervention,
    }


def test_comprehension_and_transfer_rates() -> None:
    results = [
        _result(dimensions={"comprehension": 1, "transfer": 1}),
        _result(dimensions={"comprehension": 0, "transfer": 0}),
        _result(dimensions={"comprehension": 1, "transfer": None}),
    ]
    metrics = compute_learning_metrics(results)
    assert metrics["comprehension_rate"] == 2 / 3
    assert metrics["transfer_rate"] == 0.5
    assert metrics["transfer_denominator"] == 2


def test_correction_and_recovery_rates_exclude_missing() -> None:
    results = [
        _result(dimensions={"correction": 1, "recovery": 1}),
        _result(dimensions={"correction": 0, "recovery": None}),
        _result(dimensions={"correction": None, "recovery": 0}),
    ]
    metrics = compute_learning_metrics(results)
    assert metrics["correction_rate"] == 0.5
    assert metrics["recovery_rate"] == 0.5


def test_stability_rate() -> None:
    results = [
        _result(dimensions={"stability": 1}),
        _result(dimensions={"stability": 0}),
    ]
    metrics = compute_learning_metrics(results)
    assert metrics["stability_rate"] == 0.5


def test_regression_metric_counts_confirmed_only() -> None:
    results = [
        _result(dimensions={}, regression={"confirmed_regressions": ["c-1"], "unconfirmed_flips": ["c-2"]}),
        _result(dimensions={}, regression={"confirmed_regressions": []}),
    ]
    metrics = compute_learning_metrics(results)
    assert metrics["regression_count"] == 1
    assert metrics["candidate_failed_regression"] is True


def test_human_intervention_count() -> None:
    results = [_result(dimensions={}, human_intervention=False), _result(dimensions={}, human_intervention=True)]
    metrics = compute_learning_metrics(results)
    assert metrics["human_intervention_count"] == 1
    assert metrics["human_intervention_rate"] == 0.5


def test_token_and_turn_cost_aggregates() -> None:
    results = [
        _result(dimensions={}, cost={"input_tokens": 20, "output_tokens": 10, "model_calls": 1, "turns": 2}),
        _result(dimensions={}, cost={"input_tokens": 40, "output_tokens": 30, "model_calls": 2, "turns": 4}),
    ]
    metrics = compute_learning_metrics(results)
    assert metrics["total_input_tokens"] == 60
    assert metrics["total_output_tokens"] == 40
    assert metrics["total_turns"] == 6
    assert metrics["mean_tokens_per_result"] == 50
    assert metrics["mean_turns_per_result"] == 3


def test_empty_results_report_zero_without_error() -> None:
    metrics = compute_learning_metrics([])
    assert metrics["comprehension_rate"] == 0.0
    assert metrics["total_turns"] == 0
    assert metrics["result_count"] == 0