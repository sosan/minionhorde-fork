"""Tests for task 3.3 — controlled-condition metadata for base, dogmas,
memory, and dogmas+memory+Socratic runs.

Each controlled condition declares what it activates (memory, criteria,
Socratic trajectory) so an experiment can be reproduced and audited.
Invalid combinations of activations against a condition name are
rejected at evaluation time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.controlled_condition import (
    CONTROLLED_CONDITIONS,
    ConditionSpec,
    condition_spec,
    validate_activations,
)


def test_four_controlled_conditions_exist() -> None:
    assert set(CONTROLLED_CONDITIONS) == {"base", "dogmas", "memory", "dogmas_memory_socratic"}


def test_base_does_not_require_memory_criteria_or_socratic() -> None:
    spec = condition_spec("base")
    assert spec.requires_memory is False
    assert spec.requires_criteria is False
    assert spec.requires_socratic is False


def test_dogmas_requires_criteria_only() -> None:
    spec = condition_spec("dogmas")
    assert spec.requires_criteria is True
    assert spec.requires_memory is False
    assert spec.requires_socratic is False


def test_memory_requires_memory_only() -> None:
    spec = condition_spec("memory")
    assert spec.requires_memory is True
    assert spec.requires_criteria is False
    assert spec.requires_socratic is False


def test_dogmas_memory_socratic_requires_all_three() -> None:
    spec = condition_spec("dogmas_memory_socratic")
    assert spec.requires_memory is True
    assert spec.requires_criteria is True
    assert spec.requires_socratic is True


def test_unknown_condition_raises() -> None:
    with pytest.raises(KeyError):
        condition_spec("nonexistent")


def test_validate_activations_flags_missing_requirement() -> None:
    problems = validate_activations("dogmas_memory_socratic", activations={"memory": True, "criteria": True, "socratic": False})
    assert any("socratic" in p for p in problems)


def test_validate_activations_flags_unexpected_memory_for_base() -> None:
    problems = validate_activations("base", activations={"memory": True, "criteria": False, "socratic": False})
    assert any("memory" in p for p in problems)


def test_validate_activations_clean_for_well_formed_combination() -> None:
    problems = validate_activations("dogmas_memory_socratic", activations={"memory": True, "criteria": True, "socratic": True})
    assert problems == []


def test_condition_spec_is_dataclass() -> None:
    spec = condition_spec("memory")
    assert isinstance(spec, ConditionSpec)
