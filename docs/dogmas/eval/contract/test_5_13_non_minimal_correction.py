"""Task 5.13: non-minimal correction detection (edge coverage).

A recovery is minimal only when the corrected trajectory changes exactly
the fields classified under the failure cause. Any change beyond the
allowed fields is flagged, and the extra changes are reported so they can
be recorded as separate claims requiring their own evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from trajectory_runtime import detect_non_minimal_correction


def test_identical_records_are_minimal() -> None:
    before = {"decision": "block", "evidence": "e-1"}
    result = detect_non_minimal_correction(before, dict(before), allowed_fields={"decision"})
    assert result["minimal"]
    assert result["changed_fields"] == []
    assert result["extra_fields"] == []


def test_change_restricted_to_allowed_field_is_minimal() -> None:
    before = {"decision": "block", "evidence": "e-1"}
    after = {"decision": "allow", "evidence": "e-1"}
    result = detect_non_minimal_correction(before, after, allowed_fields={"decision"})
    assert result["minimal"]
    assert result["changed_fields"] == ["decision"]
    assert result["extra_fields"] == []


def test_change_beyond_allowed_field_is_flagged() -> None:
    before = {"decision": "block", "evidence": "e-1", "metadata": "old"}
    after = {"decision": "allow", "evidence": "e-1", "metadata": "new"}
    result = detect_non_minimal_correction(before, after, allowed_fields={"decision"})
    assert not result["minimal"]
    assert "metadata" in result["extra_fields"]
    assert "decision" in result["changed_fields"]


def test_multiple_extras_are_reported_sorted() -> None:
    before = {"decision": "block", "evidence": "e-1", "scope": "a", "metadata": "old"}
    after = {"decision": "allow", "evidence": "e-2", "scope": "b", "metadata": "new"}
    result = detect_non_minimal_correction(before, after, allowed_fields={"decision"})
    assert not result["minimal"]
    assert result["extra_fields"] == ["evidence", "metadata", "scope"]


def test_added_key_is_an_extra_change() -> None:
    before = {"decision": "block"}
    after = {"decision": "allow", "new_field": "surprise"}
    result = detect_non_minimal_correction(before, after, allowed_fields={"decision"})
    assert not result["minimal"]
    assert "new_field" in result["extra_fields"]


def test_removed_key_is_an_extra_change() -> None:
    before = {"decision": "block", "removed_field": "x"}
    after = {"decision": "allow"}
    result = detect_non_minimal_correction(before, after, allowed_fields={"decision"})
    assert not result["minimal"]
    assert "removed_field" in result["extra_fields"]


def test_no_allowed_fields_makes_any_change_extra() -> None:
    before = {"decision": "block"}
    after = {"decision": "allow"}
    result = detect_non_minimal_correction(before, after, allowed_fields=set())
    assert not result["minimal"]
    assert result["extra_fields"] == ["decision"]


def test_return_shape_reports_three_fields() -> None:
    before = {"a": 1, "b": 2}
    after = {"a": 1, "b": 3}
    result = detect_non_minimal_correction(before, after, allowed_fields={"b"})
    assert set(result) == {"changed_fields", "extra_fields", "minimal"}
    assert result["changed_fields"] == ["b"]
    assert result["extra_fields"] == []
    assert result["minimal"] is True