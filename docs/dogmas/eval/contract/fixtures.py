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


def unverified_trajectory_fixture(*, condition: str = "full") -> dict:
    """Trajectory whose stored literal evidence is expired — hash-only provenance.

    No real credential or destructive operation; the only "secret-like" content
    is the synthetic placeholder ``"EXPIRED-REDACTED"`` which is not a real key.
    The fixture models the state seen when ``evidence_custody`` downgrades
    evidence from ``literal`` to ``hash_only`` because the stored literal has
    passed its ``stored_literal_expires_at``.
    """
    case = {"case_id": "synthetic/expired-evidence", "case_version": "v1", "domain": "stability"}
    case_hash = _hash(case)
    entries = build_chain([
        {
            "turn_id": "turn-001",
            "state": "INIT",
            "transition_cause": "fixture-start",
            "summary": {"decision": "expired", "fixture": True},
        },
        {
            "turn_id": "turn-002",
            "state": "EVIDENCE_CHECK",
            "transition_cause": "fixture-evidence-expired",
            "summary": {
                "decision": "downgrade",
                "evidence_mode": "hash_only",
                "stored_literal_expires_at": "2024-01-01T00:00:00Z",
                "placeholder": "EXPIRED-REDACTED",
                "fixture": True,
            },
        },
    ])
    manifest = build_manifest("trajectory-unverified-001", entries)
    policy = {"policy": "vertical_slice", "version": "v1"}
    return {
        "schema_version": "v1",
        "trajectory_id": "trajectory-unverified-001",
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
        "retrieved": {"status": "none", "items": 0, "tokens": 0, "hashes": []},
        "memory_injected": False,
        "criteria_injected": False,
        "custody_state": "OPEN",
        "terminal_state": "FAILED",
        "evaluation_validity": "limited",
        "invalidation_reason": "stored literal expired; evidence_mode=hash_only",
        "entries": entries,
        "manifest": manifest,
    }


def redacted_trajectory_fixture(*, condition: str = "full") -> dict:
    """Trajectory whose stored literal contained a secret pattern and was redacted.

    No real credential is used. The placeholder matches the
    GitHub-PAT-style redaction marker shape (``REDACTED`` token), which is the
    marker the redaction pass inserts. The fixture models the post-anatomy
    state: provenance is ``limited`` and the literal body is the redaction
    marker only.
    """
    case = {"case_id": "synthetic/secret-redacted", "case_version": "v1", "domain": "security"}
    case_hash = _hash(case)
    entries = build_chain([
        {
            "turn_id": "turn-001",
            "state": "INIT",
            "transition_cause": "fixture-start",
            "summary": {"decision": "redact", "fixture": True},
        },
        {
            "turn_id": "turn-002",
            "state": "AUDIT",
            "transition_cause": "fixture-redacted-evidence",
            "summary": {
                "decision": "block",
                "literal_redacted": True,
                "redaction_marker": "[REDACTED:github_pat]",
                "fixture": True,
            },
        },
    ])
    manifest = build_manifest("trajectory-redacted-001", entries)
    policy = {"policy": "vertical_slice", "version": "v1"}
    return {
        "schema_version": "v1",
        "trajectory_id": "trajectory-redacted-001",
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
        "retrieved": {"status": "none", "items": 0, "tokens": 0, "hashes": []},
        "memory_injected": False,
        "criteria_injected": False,
        "custody_state": "FROZEN",
        "terminal_state": "COMPLETED",
        "evaluation_validity": "limited",
        "invalidation_reason": "stored literal contained a secret; evidence_mode=hash_only",
        "entries": entries,
        "manifest": manifest,
    }


def pair_key_fixture(*, case_id: str = "synthetic/pair-key-001", repetition_id: str = "rep-001", condition: str = "base") -> dict:
    """Scenario fixture for pair-key construction (task 9.7.1).

    Two records that share case+repetition+condition MUST share the
    same ``pair_key``; records that differ in any of those three MUST
    receive a different pair key. The fixture is schema-valid.
    """
    case = {"case_id": case_id, "case_version": "v1", "domain": "stability"}
    case_hash = _hash(case)
    return {
        "schema_version": "v1",
        "result_id": f"result-{case_id}-{repetition_id}-{condition}",
        "case_id": case_id,
        "case_version": "v1",
        "case_hash": case_hash,
        "condition": condition,
        "repetition_id": repetition_id,
        "pair_key": f"{case_id}:{repetition_id}:{condition}",
        "requested_model": "fixture-model",
        "served_model": "fixture-model",
        "served_model_status": "reported",
        "sampling_parameters": {"temperature": 0},
        "case_language": "en",
        "layer_a_profile": "fixture-a",
        "layer_b_criteria_version": "fixture-b-v1",
        "layer_c_memory_version": "fixture-memory-v1",
        "policy_version": "v1",
        "policy_hash": _hash({"policy": "vertical_slice", "version": "v1"}),
        "partition_manifest_hash": _hash({"partition": "validation", "version": "v1"}),
        "timestamp": FIXTURE_TIME,
        "classification": "PASS",
        "classification_authority": "rule",
        "outcome_status": "model_pass",
        "evidence_mode": "literal",
        "provenance_status": "verified",
        "comparability": "comparable",
        "discrimination": "discriminating",
        "retrieved": {"status": "none", "items": 0},
        "dimensions": {"comprehension": 1, "correction": 1, "transfer": None, "recovery": None, "stability": 1, "regression": None},
        "evidence": {"reference_hashes": [_hash({"evidence": "synthetic"})], "tool_result_observed": False},
        "cost": {"input_tokens": 10, "output_tokens": 5, "model_calls": 1},
        "judge": {"judge_id": "rule-classifier", "model_family_relation": False, "agreement_validated": False, "condition_blinded": False},
        "missingness": {"served_model": False, "sampling": False, "evidence_reference": False, "policy_hash": True, "partition_manifest_hash": True, "judge": False},
    }


def retry_after_failure_fixture(*, case_id: str = "synthetic/retry-after-failure-001") -> dict:
    """Scenario fixture for retry-after-failure (task 9.7.2).

    The first attempt is an environment failure (``timeout``); the retry
    is a fresh pair (new repetition_id, same case+condition) that
    succeeds. Each attempt produces its own evaluation record so the
    environment failure never contributes to the model-outcome
    denominator.
    """
    first_attempt = environment_failure_fixture(
        case_id=case_id,
        outcome_status="timeout",
        repetition_id="rep-001-attempt-1",
    )
    retry = pair_key_fixture(
        case_id=case_id,
        repetition_id="rep-001-attempt-2",
        condition="base",
    )
    return {"first_attempt": first_attempt, "retry": retry}


def environment_failure_fixture(*, case_id: str = "synthetic/env-failure-001", outcome_status: str = "timeout", repetition_id: str = "rep-001") -> dict:
    """Scenario fixture for environment-failure classification (task 9.7.4).

    The record carries an environment-failure outcome (``timeout`` by
    default) and a ``missingness`` flag marking the response as absent.
    It MUST be excluded from any model-outcome denominator.
    """
    assert outcome_status in {
        "provider_error", "timeout", "credential_error",
        "budget_exceeded", "schema_invalid", "pending", "blocked", "aborted",
    }
    case = {"case_id": case_id, "case_version": "v1", "domain": "stability"}
    case_hash = _hash(case)
    return {
        "schema_version": "v1",
        "result_id": f"result-{case_id}-{repetition_id}-{outcome_status}",
        "case_id": case_id,
        "case_version": "v1",
        "case_hash": case_hash,
        "condition": "base",
        "repetition_id": repetition_id,
        "pair_key": f"{case_id}:{repetition_id}:base",
        "requested_model": "fixture-model",
        "served_model": "unknown",
        "served_model_status": "unknown",
        "sampling_parameters": {"temperature": 0},
        "case_language": "en",
        "layer_a_profile": "fixture-a",
        "layer_b_criteria_version": "fixture-b-v1",
        "layer_c_memory_version": "fixture-memory-v1",
        "policy_version": "v1",
        "policy_hash": _hash({"policy": "vertical_slice", "version": "v1"}),
        "partition_manifest_hash": _hash({"partition": "validation", "version": "v1"}),
        "timestamp": FIXTURE_TIME,
        "classification": "PARTIAL",
        "classification_authority": "rule",
        "outcome_status": outcome_status,
        "evidence_mode": "none",
        "provenance_status": "limited",
        "comparability": "non_comparable",
        "discrimination": "unknown",
        "retrieved": {"status": "none", "items": 0},
        "dimensions": {"comprehension": None, "correction": None, "transfer": None, "recovery": None, "stability": None, "regression": None},
        "evidence": {"reference_hashes": [], "tool_result_observed": False},
        "cost": {"input_tokens": None, "output_tokens": None, "model_calls": None},
        "judge": {"judge_id": "rule-classifier", "model_family_relation": False, "agreement_validated": False, "condition_blinded": False},
        "missingness": {"served_model": True, "sampling": False, "evidence_reference": True, "policy_hash": True, "partition_manifest_hash": True, "judge": False},
    }


def claim_scope_downgrade_fixture(*, candidate_id: str = "candidate-downgrade-001") -> dict:
    """Scenario fixture for claim-scope downgrade (task 9.7.5).

    The record would support a dimension-level claim but not a
    model- or global-level claim under the ``vertical_slice`` profile.
    Downgrade behavior is exercised by ``contract.profiles.restrict_claim``.
    """
    case = {"case_id": "synthetic/claim-scope-downgrade", "case_version": "v1", "domain": "stability"}
    case_hash = _hash(case)
    return {
        "schema_version": "v1",
        "result_id": f"result-{candidate_id}",
        "case_id": case["case_id"],
        "case_version": "v1",
        "case_hash": case_hash,
        "condition": "full",
        "repetition_id": "rep-001",
        "pair_key": f"{case['case_id']}:rep-001:full",
        "requested_model": "fixture-model",
        "served_model": "fixture-model",
        "served_model_status": "reported",
        "sampling_parameters": {"temperature": 0},
        "case_language": "en",
        "layer_a_profile": "fixture-a",
        "layer_b_criteria_version": "fixture-b-v1",
        "layer_c_memory_version": "fixture-memory-v1",
        "policy_version": "v1",
        "policy_hash": _hash({"policy": "vertical_slice", "version": "v1"}),
        "partition_manifest_hash": _hash({"partition": "validation", "version": "v1"}),
        "timestamp": FIXTURE_TIME,
        "classification": "PASS",
        "classification_authority": "rule",
        "outcome_status": "model_pass",
        "evidence_mode": "literal",
        "provenance_status": "verified",
        "comparability": "comparable",
        "discrimination": "discriminating",
        "retrieved": {"status": "present", "items": 1, "tokens": 12},
        "dimensions": {"comprehension": 1, "correction": 1, "transfer": 1, "recovery": None, "stability": 1, "regression": None},
        "evidence": {"reference_hashes": [_hash({"evidence": "synthetic"})], "tool_result_observed": False},
        "cost": {"input_tokens": 20, "output_tokens": 10, "model_calls": 1},
        "judge": {"judge_id": "rule-classifier", "model_family_relation": False, "agreement_validated": False, "condition_blinded": False},
        "missingness": {"served_model": False, "sampling": False, "evidence_reference": False, "policy_hash": True, "partition_manifest_hash": True, "judge": False},
    }
