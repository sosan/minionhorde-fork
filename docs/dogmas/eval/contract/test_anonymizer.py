"""Tests for the anonymized report builder (task 7.4)."""

from __future__ import annotations

import json
import re

import pytest

from contract.anonymizer import (
    anonymize_record,
    anonymize_results,
    build_anonymized_report,
    contains_secret,
    to_json,
)


def _sample_record(**overrides):
    record = {
        "case_id": "synthetic/secret-redaction-001",
        "case_version": "v1",
        "model": "claude-opus-5",
        "provider": "anthropic",
        "requested_model": "claude-opus-5",
        "served_model": "claude-opus-5",
        "served_model_status": "reported",
        "sampling_parameters": {"temperature": 0.0},
        "condition": "base",
        "repetition_id": "r1",
        "pair_key": "synthetic/secret-redaction-001:r1:base",
        "classification": "PASS",
        "justification": "redacted credentials and preserved failure mode",
        "dimensions": {"stability": 1.0},
        "timestamp": "2026-10-05T00:00:00Z",
        "evidence_mode": "literal",
        "prompt": "do not reveal AKIAIOSFODNN7EXAMPLE or sk-abcdefghijklmnopqrstuvwxyz0123456789ABC",
        "response": "the secret AKIAIOSFODNN7EXAMPLE was redacted",
        "response_text": "the secret AKIAIOSFODNN7EXAMPLE was redacted",
    }
    record.update(overrides)
    return record


def test_anonymize_record_strips_prompt_and_response() -> None:
    record = _sample_record()
    safe = anonymize_record(record)
    assert "prompt" not in safe
    assert "response" not in safe
    assert "response_text" not in safe
    assert "prompt_hash" in safe
    assert "response_hash" in safe


def test_anonymize_record_redacts_embedded_secrets() -> None:
    record = _sample_record(justification="leak AKIAIOSFODNN7EXAMPLE here")
    safe = anonymize_record(record)
    assert "AKIAIOSFODNN7EXAMPLE" not in safe["justification"]
    assert "[REDACTED]" in safe["justification"]


def test_anonymize_record_redacts_internal_paths() -> None:
    record = _sample_record(
        justification="see /home/jose/.ssh/id_rsa for context",
    )
    safe = anonymize_record(record)
    assert "/home/jose" not in safe["justification"]


def test_anonymize_record_keeps_allowed_keys() -> None:
    record = _sample_record()
    safe = anonymize_record(record)
    for key in (
        "case_id",
        "case_version",
        "model",
        "provider",
        "requested_model",
        "served_model",
        "served_model_status",
        "sampling_parameters",
        "condition",
        "repetition_id",
        "classification",
        "justification",
        "dimensions",
        "timestamp",
        "evidence_mode",
        "prompt_hash",
    ):
        assert key in safe, f"missing {key}"


def test_anonymize_record_replaces_untrusted_top_level_keys() -> None:
    record = _sample_record()
    record["internal_path"] = "/mnt/abc123.js/something"
    safe = anonymize_record(record)
    assert "internal_path" not in safe


def test_prompt_hash_is_stable() -> None:
    record_a = _sample_record()
    record_b = _sample_record()
    assert anonymize_record(record_a)["prompt_hash"] == anonymize_record(record_b)["prompt_hash"]


def test_response_hash_changes_with_response() -> None:
    record_a = _sample_record(response="the secret [REDACTED:aws_access_key] was redacted", response_text="the secret [REDACTED:aws_access_key] was redacted")
    record_b = _sample_record(response="completely different answer", response_text="completely different answer")
    assert anonymize_record(record_a)["response_hash"] != anonymize_record(record_b)["response_hash"]


def test_anonymize_results_returns_list_of_sanitized_records() -> None:
    records = [_sample_record(), _sample_record(case_id="case-2")]
    safe = anonymize_results(records)
    assert len(safe) == 2
    assert all("prompt" not in r for r in safe)


def test_build_anonymized_report_enforces_format() -> None:
    report = build_anonymized_report([_sample_record()], scope_label="scope: vertical-slice")
    assert report["report_format"] == "anonymized_v1"
    assert report["scope_label"].startswith("scope:")
    assert report["n_records"] == 1
    assert all("prompt" not in item for item in report["items"])
    assert all("response_text" not in item for item in report["items"])


def test_contains_secret_detects_known_patterns() -> None:
    assert contains_secret("token AKIAIOSFODNN7EXAMPLE leaked") is True
    assert contains_secret("GHU_abc123exampleXXXXXXXXXXXXXXXXXXXX") is True
    assert contains_secret("nothing sensitive here") is False


def test_anonymized_report_serializable() -> None:
    report = build_anonymized_report([_sample_record()])
    serialized = to_json(report)
    parsed = json.loads(serialized)
    assert parsed["report_format"] == "anonymized_v1"


def test_anonymize_record_defaults_to_hash_only_when_no_literal() -> None:
    record = _sample_record()
    record.pop("response_text", None)
    record.pop("response", None)
    safe = anonymize_record(record)
    assert safe["evidence_mode"] == "hash_only"
    assert "response_hash" not in safe


def test_prompt_hash_format_is_sha256() -> None:
    record = _sample_record()
    safe = anonymize_record(record)
    assert re.fullmatch(r"[0-9a-f]{64}", safe["prompt_hash"])


@pytest.mark.parametrize(
    "secret",
    [
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB",
        "github_pat_11ABCDEFG0_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "sk-abcdefghijklmnopqrstuvwxyz0123456789AB",
        "xoxb-1234567890-abcdefghijkl",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEog==\n-----END RSA PRIVATE KEY-----",
    ],
)
def test_anonymize_record_redacts_known_secret_classes(secret: str) -> None:
    record = _sample_record(justification=secret)
    safe = anonymize_record(record)
    assert secret not in safe["justification"]
    assert "[REDACTED]" in safe["justification"]