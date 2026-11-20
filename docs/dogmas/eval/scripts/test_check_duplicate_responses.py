"""Tests for duplicate response detection."""

from __future__ import annotations

import json
from pathlib import Path

from check_duplicate_responses import audit, load_baseline, response_hash


def write_record(registry: Path, repetition: str, literal: str) -> None:
    path = registry / "case" / "model" / f"{repetition}-C0.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "case_id": "synthetic/case-001",
                "model": "model",
                "repetition_id": repetition,
                "condition": "C0",
                "response_literal": literal,
            }
        ),
        encoding="utf-8",
    )


def test_whitespace_differences_hash_equally():
    assert response_hash("a  b\n") == response_hash("a b")


def test_copied_literal_is_reported(tmp_path):
    write_record(tmp_path, "r01", "Decision: failed.")
    write_record(tmp_path, "r02", "Decision:  failed.")
    report = audit(tmp_path, set())
    assert report["duplicate_groups"] == 1
    assert report["duplicate_records"] == 2


def test_distinct_literals_are_not_reported(tmp_path):
    write_record(tmp_path, "r01", "Decision: failed.")
    write_record(tmp_path, "r02", "Decision: passed.")
    assert audit(tmp_path, set())["duplicate_groups"] == 0


def test_baseline_separates_known_from_new(tmp_path):
    write_record(tmp_path, "r01", "Decision: failed.")
    write_record(tmp_path, "r02", "Decision: failed.")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"known_duplicate_hashes": [response_hash("Decision: failed.")]}),
        encoding="utf-8",
    )
    report = audit(tmp_path, load_baseline(baseline))
    assert report["new_duplicate_hashes"] == []
    assert len(report["known_duplicate_hashes"]) == 1
