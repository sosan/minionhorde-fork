"""Controlled-condition metadata (task 3.3).

An experiment runs under one of four controlled conditions: ``base``,
``dogmas``, ``memory``, or ``dogmas_memory_socratic``. Each condition
declares which activations are expected (memory injection, criteria
injection, Socratic trajectory). ``validate_activations`` rejects
combinations that contradict the declared condition, so an experiment
cannot silently run under the wrong activations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ConditionSpec:
    """What a controlled condition activates and requires."""

    name: str
    requires_memory: bool
    requires_criteria: bool
    requires_socratic: bool
    notes: str = ""

    def activation_tuple(self) -> tuple[bool, bool, bool]:
        return (self.requires_memory, self.requires_criteria, self.requires_socratic)


CONTROLLED_CONDITIONS: dict[str, ConditionSpec] = {
    "base": ConditionSpec("base", False, False, False, notes="no injections; control run"),
    "dogmas": ConditionSpec("dogmas", False, True, False, notes="criteria (dogmas) injected"),
    "memory": ConditionSpec("memory", True, False, False, notes="memory injected, no criteria"),
    "dogmas_memory_socratic": ConditionSpec(
        "dogmas_memory_socratic",
        True,
        True,
        True,
        notes="criteria + memory + Socratic trajectory",
    ),
}


def condition_spec(name: str) -> ConditionSpec:
    """Return the spec for a controlled condition; raises on unknown names."""
    try:
        return CONTROLLED_CONDITIONS[name]
    except KeyError:
        raise KeyError(
            f"unknown controlled condition: {name!r}; available: {sorted(CONTROLLED_CONDITIONS)}"
        ) from None


def validate_activations(name: str, activations: Mapping[str, bool]) -> list[str]:
    """Verify that the actual activations match the condition's requirements.

    Returns a list of problems (empty when the combination is well
    formed). ``activations`` keys: ``memory``, ``criteria``, ``socratic``.
    """
    spec = condition_spec(name)
    problems: list[str] = []
    expected = {
        "memory": spec.requires_memory,
        "criteria": spec.requires_criteria,
        "socratic": spec.requires_socratic,
    }
    for activation, required in expected.items():
        actual = bool(activations.get(activation, False))
        if required and not actual:
            problems.append(f"{activation} is required by {name} but was not activated")
        if actual and not required:
            problems.append(f"{activation} was activated but is not part of {name}")
    return problems
