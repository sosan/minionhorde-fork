"""Separated metric breakdown (task 3.4).

Validation and metrics must report provenance, coverage, dissent,
confidence intervals, and cost SEPARATELY. ``compute_breakdown``
aggregates results into a structured report where each dimension is its
own top-level key; consumers recompute a dimension without touching the
others.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def _clean_cost(record: Mapping[str, Any]) -> tuple[int, int, int]:
    cost = record.get("cost") or {}
    return (
        int(cost.get("input_tokens") or 0),
        int(cost.get("output_tokens") or 0),
        int(cost.get("model_calls") or 0),
    )


def compute_breakdown(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate results into per-dimension metric buckets.

    Returns a dict with independent ``provenance``, ``coverage``,
    ``dissent``, ``cost``, and ``confidence_intervals`` sections.
    """
    provenance: dict[str, int] = {}
    coverage: dict[str, int] = {}
    dissent_open = 0
    dissent_resolved = 0
    total_input = 0
    total_output = 0
    total_calls = 0
    ci_low: list[float] = []
    ci_center: list[float] = []
    ci_high: list[float] = []

    for record in results:
        prov = record.get("provenance_status")
        if prov:
            provenance[prov] = provenance.get(prov, 0) + 1

        cov = record.get("coverage_status")
        if cov:
            coverage[cov] = coverage.get(cov, 0) + 1

        if record.get("dissent_open"):
            dissent_open += 1
        else:
            dissent_resolved += 1

        input_tokens, output_tokens, calls = _clean_cost(record)
        total_input += input_tokens
        total_output += output_tokens
        total_calls += calls

        ci = record.get("confidence_interval")
        if isinstance(ci, (tuple, list)) and len(ci) == 3:
            ci_low.append(float(ci[0]))
            ci_high.append(float(ci[1]))
            ci_center.append(float(ci[2]))

    return {
        "provenance": provenance,
        "coverage": coverage,
        "dissent": {"open": dissent_open, "resolved": dissent_resolved},
        "cost": {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_model_calls": total_calls,
        },
        "confidence_intervals": {
            "count": len(ci_low),
            "low": ci_low,
            "high": ci_high,
            "center": ci_center,
        },
    }
