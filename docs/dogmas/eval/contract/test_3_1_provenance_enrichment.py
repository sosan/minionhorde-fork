"""Tests for task 3.1 — extend evaluation results to record evidence mode,
evaluator authority, observable tool outcome availability, and
configuration hashes.

The result exposes builders for each block (``build_evidence_block``,
``build_judge_block``, ``build_cost_block``) and an
``enrich_evaluation_result`` that fills them from a single call. A
configuration hash captures the policy + partition + trajectory hashes
that produced the result.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.provenance_enrichment import (
    build_configuration_hash,
    build_cost_block,
    build_evidence_block,
    build_judge_block,
    enrich_evaluation_result,
)


def test_build_evidence_block_records_tool_observed() -> None:
    block = build_evidence_block(
        reference_hashes=["a" * 64],
        tool_result_observed=True,
        custody_id="custody-1",
        custody_state="OPEN",
    )
    assert block["tool_result_observed"] is True
    assert block["reference_hashes"] == ["a" * 64]
    assert block["custody_id"] == "custody-1"
    assert block["custody_state"] == "OPEN"


def test_build_evidence_block_marks_tool_not_observed() -> None:
    block = build_evidence_block(reference_hashes=[], tool_result_observed=False)
    assert block["tool_result_observed"] is False
    assert block["custody_id"] is None


def test_build_judge_block_records_identity_and_blinding() -> None:
    block = build_judge_block(
        judge_id="judge-1",
        model_family_relation=True,
        condition_blinded=True,
        agreement_validated=False,
    )
    assert block["judge_id"] == "judge-1"
    assert block["model_family_relation"] is True
    assert block["condition_blinded"] is True
    assert block["agreement_validated"] is False


def test_build_cost_block_records_tokens_and_calls() -> None:
    block = build_cost_block(input_tokens=120, output_tokens=80, model_calls=3)
    assert block == {"input_tokens": 120, "output_tokens": 80, "model_calls": 3}


def test_build_configuration_hash_is_stable_and_changes_with_inputs() -> None:
    h1 = build_configuration_hash(policy_hash="p" * 64, partition_manifest_hash="q" * 64, trajectory_hash="t" * 64)
    h2 = build_configuration_hash(policy_hash="p" * 64, partition_manifest_hash="q" * 64, trajectory_hash="t" * 64)
    assert h1 == h2
    assert len(h1) == 64
    assert h1 != build_configuration_hash(policy_hash="x" * 64, partition_manifest_hash="q" * 64, trajectory_hash="t" * 64)


def test_enrich_evaluation_result_populates_all_blocks() -> None:
    result = {
        "result_id": "r1",
        "evidence": {},
        "judge": {},
        "cost": {},
        "configuration_hash": None,
    }
    enrich_evaluation_result(
        result,
        reference_hashes=["a" * 64],
        tool_result_observed=True,
        custody_id="custody-1",
        custody_state="OPEN",
        judge_id="judge-1",
        model_family_relation=False,
        condition_blinded=True,
        input_tokens=100,
        output_tokens=50,
        model_calls=1,
        policy_hash="p" * 64,
        partition_manifest_hash="q" * 64,
        trajectory_hash="t" * 64,
    )
    assert result["evidence"]["tool_result_observed"] is True
    assert result["judge"]["judge_id"] == "judge-1"
    assert result["cost"] == {"input_tokens": 100, "output_tokens": 50, "model_calls": 1}
    assert result["configuration_hash"] is not None
    assert len(result["configuration_hash"]) == 64
