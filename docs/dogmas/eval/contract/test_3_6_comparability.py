"""Tests for task 3.6 — record served_model/sampling/case_language and mark
non-comparable when configuration differs.

Per evaluation record: requested_model, served_model, sampling_parameters,
and case_language are recorded. When two records are compared for the
same case under different configurations, comparability MUST be
``non_comparable`` if served_model or sampling_parameters differ; the
record's own ``comparability`` field is set according to whether its own
configuration matches the canonical (reference) configuration.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.comparability import (
    assess_pair,
    record_comparability,
    reference_configuration,
)


def _result(**kwargs):
    base = {
        "result_id": "r1",
        "case_id": "c1",
        "requested_model": "claude-opus-4",
        "served_model": "claude-opus-4",
        "sampling_parameters": {"temperature": 0.0},
        "case_language": "en",
        "classification_authority": "rule",
    }
    base.update(kwargs)
    return base


def test_reference_configuration_captures_served_model_and_sampling() -> None:
    ref = reference_configuration(served_model="claude-opus-4", sampling={"temperature": 0.0}, case_language="en")
    assert ref["served_model"] == "claude-opus-4"
    assert ref["sampling_parameters"]["temperature"] == 0.0
    assert ref["case_language"] == "en"


def test_record_comparability_marks_comparable_when_match() -> None:
    record = _result()
    record_comparability(record, reference_configuration(served_model="claude-opus-4", sampling={"temperature": 0.0}, case_language="en"))
    assert record["comparability"] == "comparable"


def test_record_comparability_marks_non_comparable_when_served_model_differs() -> None:
    record = _result(served_model="claude-haiku-4")
    record_comparability(record, reference_configuration(served_model="claude-opus-4", sampling={"temperature": 0.0}, case_language="en"))
    assert record["comparability"] == "non_comparable"


def test_record_comparability_marks_non_comparable_when_sampling_differs() -> None:
    record = _result(sampling_parameters={"temperature": 0.5, "top_p": 1.0})
    record_comparability(record, reference_configuration(served_model="claude-opus-4", sampling={"temperature": 0.0}, case_language="en"))
    assert record["comparability"] == "non_comparable"


def test_record_comparability_marks_provisional_when_authority_unknown() -> None:
    record = _result(classification_authority="unverified")
    record_comparability(record, reference_configuration(served_model="claude-opus-4", sampling={"temperature": 0.0}, case_language="en"))
    assert record["comparability"] == "provisional"


def test_assess_pair_reports_configuration_diff() -> None:
    a = _result(served_model="claude-opus-4")
    b = _result(served_model="claude-haiku-4")
    report = assess_pair(a, b)
    assert report["comparable"] is False
    assert "served_model" in report["differences"]


def test_assess_pair_marks_comparable_when_config_matches() -> None:
    a = _result()
    b = _result()
    report = assess_pair(a, b)
    assert report["comparable"] is True
    assert report["differences"] == []


def test_assess_pair_never_raises_on_missing_fields() -> None:
    a = {"result_id": "a"}
    b = {"result_id": "b"}
    report = assess_pair(a, b)
    assert "comparable" in report
    assert "differences" in report
