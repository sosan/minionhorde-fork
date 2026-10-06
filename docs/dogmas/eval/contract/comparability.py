"""Configuration comparison for evaluation records (task 3.6).

Every evaluation result records ``requested_model``, ``served_model``,
``sampling_parameters``, and ``case_language``. When results are compared
across configurations, comparability MUST be ``non_comparable`` when the
served model or sampling parameters differ, ``comparable`` when they
match, and ``provisional`` when the classification authority is not yet
validated.
"""

from __future__ import annotations

from typing import Any, Mapping


def reference_configuration(*, served_model: str, sampling: Mapping[str, Any], case_language: str) -> dict[str, Any]:
    """Capture the canonical configuration a batch of results runs under."""
    return {
        "served_model": served_model,
        "sampling_parameters": dict(sampling),
        "case_language": case_language,
    }


def _configuration_matches(record: Mapping[str, Any], reference: Mapping[str, Any]) -> tuple[bool, list[str]]:
    differences: list[str] = []
    served = record.get("served_model")
    if served is not None and reference.get("served_model") is not None and served != reference["served_model"]:
        differences.append("served_model")
    sampling = record.get("sampling_parameters")
    if isinstance(sampling, Mapping) and isinstance(reference.get("sampling_parameters"), Mapping):
        if dict(sampling) != dict(reference["sampling_parameters"]):
            differences.append("sampling_parameters")
    return not differences, differences


def record_comparability(record: dict[str, Any], reference: Mapping[str, Any]) -> dict[str, Any]:
    """Set ``record['comparability']`` against the reference configuration.

    ``comparable`` when the configuration matches; ``non_comparable`` when
    served model or sampling differ; ``provisional`` when the
    classification authority is not validated.
    """
    matches, _ = _configuration_matches(record, reference)
    if not matches:
        record["comparability"] = "non_comparable"
        return record
    authority = record.get("classification_authority")
    if authority in (None, "unverified", "judge"):
        record["comparability"] = "provisional"
        return record
    record["comparability"] = "comparable"
    return record


def assess_pair(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two records for the same case.

    Never raises on missing fields; a missing configuration value simply
    contributes no difference.
    """
    differences: list[str] = []
    for field in ("served_model", "sampling_parameters"):
        value_a = a.get(field)
        value_b = b.get(field)
        if isinstance(value_a, Mapping) and isinstance(value_b, Mapping):
            if dict(value_a) != dict(value_b):
                differences.append(field)
        elif value_a is not None and value_b is not None and value_a != value_b:
            differences.append(field)
    return {"comparable": not differences, "differences": differences}
