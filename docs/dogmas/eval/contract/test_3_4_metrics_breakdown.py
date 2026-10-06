"""Tests for task 3.4 — report provenance, coverage, dissent, confidence
intervals, and cost SEPARATELY in metrics.

A single ``compute_breakdown`` aggregates results into a structured
report. Each dimension (provenance, coverage, dissent, ci, cost) is
exposed independently so downstream consumers can recompute them in
isolation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.metrics_breakdown import compute_breakdown


def _r(*, prov: str, cost_in: int = 0, cost_out: int = 0, calls: int = 0, ci: tuple[float, float, float] | None = None, dissent: bool = False) -> dict:
    return {
        "result_id": f"r-{prov}-{cost_in}-{dissent}",
        "provenance_status": prov,
        "cost": {"input_tokens": cost_in, "output_tokens": cost_out, "model_calls": calls},
        "comparability": "comparable",
        "coverage_status": "covered" if prov == "verified" else "limited",
        "judge": {"agreement_validated": prov == "verified"},
        "dissent_open": dissent,
        "confidence_interval": ci,
    }


def test_breakdown_partitions_by_provenance_status() -> None:
    report = compute_breakdown([_r(prov="verified"), _r(prov="verified"), _r(prov="limited"), _r(prov="unverified")])
    assert report["provenance"]["verified"] == 2
    assert report["provenance"]["limited"] == 1
    assert report["provenance"]["unverified"] == 1


def test_breakdown_separates_coverage_counts() -> None:
    report = compute_breakdown([_r(prov="verified"), _r(prov="verified"), _r(prov="limited")])
    assert report["coverage"]["covered"] == 2
    assert report["coverage"]["limited"] == 1


def test_breakdown_separates_dissent_open_vs_resolved() -> None:
    report = compute_breakdown([_r(prov="verified"), _r(prov="verified", dissent=True), _r(prov="limited")])
    assert report["dissent"]["open"] == 1
    assert report["dissent"]["resolved"] == 2


def test_breakdown_aggregates_cost_separately() -> None:
    report = compute_breakdown([_r(prov="verified", cost_in=100, cost_out=50, calls=1), _r(prov="verified", cost_in=200, cost_out=80, calls=2)])
    assert report["cost"]["total_input_tokens"] == 300
    assert report["cost"]["total_output_tokens"] == 130
    assert report["cost"]["total_model_calls"] == 3


def test_breakdown_exposes_confidence_intervals_separately() -> None:
    ci = (0.40, 0.50, 0.45)
    report = compute_breakdown([_r(prov="verified", ci=ci), _r(prov="verified")])
    assert report["confidence_intervals"]["count"] == 1
    assert report["confidence_intervals"]["low"][0] == 0.40
    assert report["confidence_intervals"]["center"][0] == 0.45


def test_breakdown_handles_empty_input() -> None:
    report = compute_breakdown([])
    assert report["provenance"] == {}
    assert report["cost"]["total_input_tokens"] == 0
    assert report["confidence_intervals"]["count"] == 0


def test_breakdown_never_mixes_provenance_with_cost() -> None:
    report = compute_breakdown([_r(prov="verified", cost_in=10)])
    assert "verified" in report["provenance"]
    assert "total_input_tokens" in report["cost"]
    assert "verified" not in report["cost"]
