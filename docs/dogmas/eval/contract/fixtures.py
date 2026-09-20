"""Deterministic, credential-free fixtures for the modern evaluation contract."""

from __future__ import annotations

from datetime import datetime, timezone

from .canonical import digest
from .integrity import build_chain, build_manifest

FIXTURE_TIME = "2026-01-01T00:00:00Z"


def _hash(value: object) -> str:
    return digest(value)


def trajectory_fixture(
    *,
    condition: str = "full",
    retrieved_status: str = "present",
    terminal_state: str = "COMPLETED",
    custody_state: str = "FROZEN",
) -> dict:
    case = {"case_id": "synthetic/security-boundary", "case_version": "v1", "domain": "security"}
    case_hash = _hash(case)
    retrieved_hash = _hash({"candidate_id": "candidate-1", "version": "v1"})
    retrieved = {
        "status": retrieved_status,
        "items": 1 if retrieved_status == "present" else 0,
        "tokens": 24 if retrieved_status == "present" else 0,
        "hashes": [retrieved_hash] if retrieved_status == "present" else [],
    }
    entries = build_chain([
        {
            "turn_id": "turn-001",
            "state": "INIT",
            "transition_cause": "fixture-start",
            "summary": {"decision": "block", "fixture": True},
        },
        {
            "turn_id": "turn-002",
            "state": "AUDIT",
            "transition_cause": "fixture-evidence",
            "summary": {"decision": "block", "fixture": True},
            "evidence_hashes": [_hash({"evidence": "synthetic"})],
        },
    ])
    manifest = build_manifest("trajectory-synthetic-001", entries)
    policy = {"policy": "vertical_slice", "version": "v1"}
    return {
        "schema_version": "v1",
        "trajectory_id": "trajectory-synthetic-001",
        "case_id": case["case_id"],
        "case_version": case["case_version"],
        "case_hash": case_hash,
        "condition": condition,
        "requested_model": "fixture-model",
        "served_model": "fixture-model",
        "served_model_status": "reported",
        "sampling_parameters": {"temperature": 0},
        "case_language": "en",
        "layer_a_profile": "fixture-a",
        "layer_b_criteria_version": "fixture-b-v1",
        "layer_c_memory_version": "fixture-memory-v1",
        "policy_version": "v1",
        "process_policy_hash": _hash(policy),
        "prompt_template_hash": _hash({"template": "fixture-template-v1"}),
        "prompt_context_hash": _hash({"context": "fixture-context-v1", "condition": condition}),
        "retrieved": retrieved,
        "memory_injected": condition in {"criteria_memory", "full"} and retrieved_status == "present",
        "criteria_injected": condition in {"criteria", "criteria_memory", "full"},
        "custody_state": custody_state,
        "terminal_state": terminal_state,
        "entries": entries,
        "manifest": manifest,
    }


def evaluation_fixture(*, outcome_status: str = "model_pass", condition: str = "full") -> dict:
    case = {"case_id": "synthetic/security-boundary", "case_version": "v1", "variant_class": "direct"}
    case_hash = _hash(case)
    policy_hash = _hash({"policy": "vertical_slice", "version": "v1"})
    return {
        "schema_version": "v1",
        "result_id": "result-synthetic-001",
        "case_id": case["case_id"],
        "case_version": case["case_version"],
        "case_hash": case_hash,
        "condition": condition,
        "repetition_id": "rep-001",
        "pair_key": "synthetic/security-boundary:v1:rep-001",
        "requested_model": "fixture-model",
        "served_model": "fixture-model",
        "served_model_status": "reported",
        "sampling_parameters": {"temperature": 0},
        "case_language": "en",
        "layer_a_profile": "fixture-a",
        "layer_b_criteria_version": "fixture-b-v1",
        "layer_c_memory_version": "fixture-memory-v1",
        "policy_version": "v1",
        "policy_hash": policy_hash,
        "partition_manifest_hash": _hash({"partition": "validation", "version": "v1"}),
        "timestamp": FIXTURE_TIME,
        "classification": "PASS" if outcome_status == "model_pass" else "FAIL",
        "classification_authority": "rule",
        "outcome_status": outcome_status,
        "evidence_mode": "literal",
        "provenance_status": "verified",
        "comparability": "comparable" if outcome_status == "model_pass" else "provisional",
        "discrimination": "discriminating",
        "retrieved": {"status": "present", "items": 1, "hashes": [_hash({"candidate_id": "candidate-1"})], "tokens": 12},
        "dimensions": {"comprehension": 1, "correction": 1, "transfer": 1, "recovery": None, "stability": None, "regression": None},
        "evidence": {"reference_hashes": [_hash({"evidence": "synthetic"})], "tool_result_observed": False},
        "cost": {"input_tokens": 20, "output_tokens": 10, "model_calls": 1},
    }


def legacy_limited_fixture() -> dict:
    return {
        "case_id": "legacy/case-01",
        "model": "legacy-model",
        "provider": "fixture",
        "classification": "PASS",
        "justification": "synthetic legacy summary",
        "timestamp": FIXTURE_TIME,
        "provenance_status": "legacy_limited",
        "classification_authority": "unverified",
        "served_model": "unknown",
        "sampling_parameters": "unknown",
        "evidence_mode": "summary",
    }
