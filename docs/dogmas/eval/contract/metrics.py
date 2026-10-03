"""Learning-outcome metrics (task 5.4).

Aggregates per-result dimensions into rates for comprehension, correction,
transfer, recovery, and stability, plus regression counts, human
intervention, and token/turn cost. Missing dimensions (None) contribute to
the denominator only when the dimension was measured.
"""

from __future__ import annotations

from typing import Any

LEARNING_DIMENSIONS = ("comprehension", "correction", "transfer", "recovery", "stability")


def _rate(values: list[int]) -> tuple[float, int]:
    """Mean over present binary values; (0.0, 0) when nothing was measured."""
    if not values:
        return 0.0, 0
    return sum(values) / len(values), len(values)


def compute_learning_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate learning metrics from evaluation results.

    Each result may carry ``dimensions`` (per-dimension 0/1/None),
    ``cost`` (input_tokens, output_tokens, model_calls, turns),
    ``regression`` (confirmed_regressions, unconfirmed_flips), and
    ``human_intervention`` (bool).
    """
    dimension_values: dict[str, list[int]] = {dim: [] for dim in LEARNING_DIMENSIONS}
    total_input = total_output = total_calls = total_turns = 0
    intervention_count = regression_count = 0
    failed_regression = False

    for result in results:
        dimensions = result.get("dimensions") or {}
        for dim in LEARNING_DIMENSIONS:
            value = dimensions.get(dim)
            if value is not None:
                dimension_values[dim].append(int(bool(value)))
        cost = result.get("cost") or {}
        total_input += int(cost.get("input_tokens", 0))
        total_output += int(cost.get("output_tokens", 0))
        total_calls += int(cost.get("model_calls", 0))
        total_turns += int(cost.get("turns", 0))
        intervention_count += 1 if result.get("human_intervention") else 0
        regression = result.get("regression") or {}
        confirmed = regression.get("confirmed_regressions") or []
        regression_count += len(confirmed)
        failed_regression = failed_regression or bool(confirmed)

    count = len(results)
    metrics: dict[str, Any] = {"result_count": count}
    for dim in LEARNING_DIMENSIONS:
        rate, denominator = _rate(dimension_values[dim])
        metrics[f"{dim}_rate"] = rate
        metrics[f"{dim}_denominator"] = denominator
    metrics.update(
        {
            "regression_count": regression_count,
            "candidate_failed_regression": failed_regression,
            "human_intervention_count": intervention_count,
            "human_intervention_rate": (intervention_count / count) if count else 0.0,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_model_calls": total_calls,
            "total_turns": total_turns,
            "mean_tokens_per_result": (total_input + total_output) / count if count else 0.0,
            "mean_turns_per_result": total_turns / count if count else 0.0,
        }
    )
    return metrics