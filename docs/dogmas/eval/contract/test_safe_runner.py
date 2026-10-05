"""Tests for the safe-suite runner (task 7.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contract.safe_runner import SAFE_CASES, run_safe_suite
from contract.coverage_gates import CoverageConfig


def test_safe_runner_emits_full_artifact_set(tmp_path: Path) -> None:
    summary = run_safe_suite(tmp_path)
    for filename in (
        "safe_runner_manifest.json",
        "safe_runner_envelopes.json",
        "safe_runner_classifications.json",
        "safe_runner_anonymized_report.json",
        "safe_runner_coverage_gates.json",
        "safe_runner_summary.json",
    ):
        path = tmp_path / filename
        assert path.exists(), f"missing {filename}"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload, f"empty artifact: {filename}"


def test_safe_runner_includes_all_cases_and_conditions(tmp_path: Path) -> None:
    summary = run_safe_suite(tmp_path)
    classifications = json.loads((tmp_path / "safe_runner_classifications.json").read_text(encoding="utf-8"))
    assert len(classifications) == len(SAFE_CASES) * 4
    cases_in_payload = {record["case_id"] for record in classifications}
    assert cases_in_payload == set(SAFE_CASES)


def test_safe_runner_records_blocked_high_confidence_scopes(tmp_path: Path) -> None:
    summary = run_safe_suite(tmp_path)
    manifest = json.loads((tmp_path / "safe_runner_manifest.json").read_text(encoding="utf-8"))
    assert manifest["adapter"] == "echo"
    assert manifest["cases"] == list(SAFE_CASES)
    assert manifest["envelope_count"] == len(SAFE_CASES)
    assert manifest["classification_count"] == len(SAFE_CASES) * 4


def test_safe_runner_anonymized_report_contains_no_prompts(tmp_path: Path) -> None:
    run_safe_suite(tmp_path)
    report = json.loads((tmp_path / "safe_runner_anonymized_report.json").read_text(encoding="utf-8"))
    assert report["report_format"] == "anonymized_v1"
    assert all("prompt" not in item for item in report["items"])
    assert all("response_text" not in item for item in report["items"])


def test_safe_runner_coverage_gates_block_global_by_default(tmp_path: Path) -> None:
    run_safe_suite(tmp_path)
    gates = json.loads((tmp_path / "safe_runner_coverage_gates.json").read_text(encoding="utf-8"))
    assert gates["case"]["verdict"] in {"preliminary", "pass"}
    assert gates["global"]["verdict"] == "block"
    assert any(
        reason in " ".join(gates["global"]["reasons"])
        for reason in ("repetitions_under", "provenance_insufficient", "high_confidence_scope")
    )


def test_safe_runner_supports_custom_threshold(tmp_path: Path) -> None:
    cfg = CoverageConfig(min_repetitions=1, min_categories=1)
    summary = run_safe_suite(tmp_path, config=cfg)
    gates = json.loads((tmp_path / "safe_runner_coverage_gates.json").read_text(encoding="utf-8"))
    assert gates["dimension"]["verdict"] in {"preliminary", "pass"}
    assert gates["global"]["verdict"] in {"preliminary", "block"}


def test_safe_runner_envelopes_never_persist_responses(tmp_path: Path) -> None:
    run_safe_suite(tmp_path)
    envelopes = json.loads((tmp_path / "safe_runner_envelopes.json").read_text(encoding="utf-8"))
    for envelope in envelopes:
        assert "response_text" not in envelope
        assert "response_hash" in envelope


def test_safe_runner_manifest_records_config(tmp_path: Path) -> None:
    cfg = CoverageConfig(min_repetitions=3, min_categories=2)
    run_safe_suite(tmp_path, config=cfg)
    manifest = json.loads((tmp_path / "safe_runner_manifest.json").read_text(encoding="utf-8"))
    assert manifest["coverage_config"]["min_repetitions"] == 3
    assert manifest["coverage_config"]["min_categories"] == 2


def test_safe_runner_classifications_have_provenance(tmp_path: Path) -> None:
    run_safe_suite(tmp_path)
    records = json.loads((tmp_path / "safe_runner_classifications.json").read_text(encoding="utf-8"))
    for record in records:
        assert "evidence_mode" in record
        assert "provenance_status" in record
        assert "category" in record
        assert "dimension" in record