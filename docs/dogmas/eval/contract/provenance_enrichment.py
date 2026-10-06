"""Evaluation-result enrichment blocks (task 3.1).

Builders for the evidence, judge, and cost blocks of an evaluation
result, plus a configuration hash that captures the policy, partition
manifest, and trajectory that produced the result. ``enrich_evaluation_result``
fills them in one call, keeping the result schema-valid.
"""

from __future__ import annotations

from typing import Any, Mapping

from .canonical import digest


def build_evidence_block(
    *,
    reference_hashes: list[str],
    tool_result_observed: bool,
    custody_id: str | None = None,
    custody_state: str | None = None,
) -> dict[str, Any]:
    """Build the ``evidence`` sub-document of an evaluation result."""
    return {
        "reference_hashes": list(reference_hashes),
        "tool_result_observed": bool(tool_result_observed),
        "custody_id": custody_id,
        "custody_state": custody_state,
    }


def build_judge_block(
    *,
    judge_id: str,
    model_family_relation: bool,
    condition_blinded: bool,
    agreement_validated: bool = False,
) -> dict[str, Any]:
    """Build the ``judge`` sub-document of an evaluation result."""
    return {
        "judge_id": judge_id,
        "model_family_relation": bool(model_family_relation),
        "agreement_validated": bool(agreement_validated),
        "condition_blinded": bool(condition_blinded),
    }


def build_cost_block(
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    model_calls: int | None = None,
) -> dict[str, Any]:
    """Build the ``cost`` sub-document of an evaluation result."""
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_calls": model_calls,
    }


def build_configuration_hash(
    *,
    policy_hash: str,
    partition_manifest_hash: str,
    trajectory_hash: str,
) -> str:
    """Hash the configuration that produced a result.

    Stable across processes: uses the canonical digest over the three
    component hashes.
    """
    return digest(
        {
            "policy_hash": policy_hash,
            "partition_manifest_hash": partition_manifest_hash,
            "trajectory_hash": trajectory_hash,
        }
    )


def enrich_evaluation_result(result: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Fill evidence, judge, cost, and configuration hash on ``result``.

    Accepts the keyword arguments of the three builders plus
    ``policy_hash``, ``partition_manifest_hash``, and ``trajectory_hash``.
    Missing builder kwargs fall back to ``None``/``[]`` so the call stays
    schema-valid.
    """
    result["evidence"] = build_evidence_block(
        reference_hashes=kwargs.get("reference_hashes", []),
        tool_result_observed=kwargs.get("tool_result_observed", False),
        custody_id=kwargs.get("custody_id"),
        custody_state=kwargs.get("custody_state"),
    )
    result["judge"] = build_judge_block(
        judge_id=kwargs.get("judge_id", ""),
        model_family_relation=kwargs.get("model_family_relation", False),
        condition_blinded=kwargs.get("condition_blinded", False),
        agreement_validated=kwargs.get("agreement_validated", False),
    )
    result["cost"] = build_cost_block(
        input_tokens=kwargs.get("input_tokens"),
        output_tokens=kwargs.get("output_tokens"),
        model_calls=kwargs.get("model_calls"),
    )
    if kwargs.get("policy_hash") or kwargs.get("partition_manifest_hash") or kwargs.get("trajectory_hash"):
        result["configuration_hash"] = build_configuration_hash(
            policy_hash=kwargs.get("policy_hash", ""),
            partition_manifest_hash=kwargs.get("partition_manifest_hash", ""),
            trajectory_hash=kwargs.get("trajectory_hash", ""),
        )
    return result
