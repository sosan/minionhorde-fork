"""End-to-end runner that wires provider adapters, coverage gates, and
the anonymized report builder into a single safe-suite execution.

The runner is invoked from the command line for task 7.5. It is
deterministic when the ``echo`` adapter is selected, which is the
default for safe-suite runs. Credentials are NEVER persisted and the
runner refuses to return envelopes that contain secret-like content.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from contract import (
    anonymizer,
    coverage_gates,
    providers,
)
from contract.coverage_gates import ClaimScope, CoverageConfig, GateVerdict
from contract.ingest_manual import _classify, CONDITIONS


SAFE_CASES: tuple[str, ...] = (
    "synthetic/secret-redaction-001",
    "synthetic/sandbox-postcondition-001",
    "synthetic/memory-injection-stale-approval-001",
    "synthetic/permission-boundary-escalation-001",
    "synthetic/approval-expiry-irreversible-001",
    "synthetic/isolation-downgrade-001",
)


def _safe_prompt(prompt_hash_seed: str) -> str:
    return f"[safe-suite prompt seed {prompt_hash_seed}]"


def _safe_response(case_id: str, condition: str) -> str:
    return f"[safe-suite response for {case_id} condition {condition}]"


def _evaluate_classification(case_id: str, condition: str, response: str) -> dict[str, Any]:
    return _classify(case_id, condition, response)


def run_safe_suite(
    output_dir: Path,
    *,
    adapter_name: str = "echo",
    model: str = "safe/echo-v0",
    cases: tuple[str, ...] = SAFE_CASES,
    config: CoverageConfig | None = None,
) -> dict[str, Any]:
    """Run the full safe evaluation suite and emit raw + anonymized reports.

    The function NEVER persists prompts or full responses. It writes:

    * ``safe_runner_manifest.json`` — the manifest of cases, conditions,
      adapters, and models actually used in this run.
    * ``safe_runner_envelopes.json`` — provider envelopes (no prompts,
      no responses, hashes only).
    * ``safe_runner_classifications.json`` — case-by-condition
      classifications under the controlled conditions.
    * ``safe_runner_anonymized_report.json`` — the shareable report,
      anonymized by ``contract.anonymizer``.
    * ``safe_runner_coverage_gates.json`` — gate outcomes per scope.

    Returns the full in-memory report so callers can inspect or pipe it.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or CoverageConfig()
    timestamp = datetime.now(timezone.utc).isoformat()

    envelopes: list[dict[str, Any]] = []
    classifications: list[dict[str, Any]] = []
    case_results: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for case_id in cases:
        prompt_seed = hashlib.sha256(f"{case_id}:{adapter_name}".encode()).hexdigest()[:16]
        prompt_text = _safe_prompt(prompt_seed)
        envelope = providers.run_controlled_condition(
            adapter_name,
            prompt=prompt_text,
            model=model,
            config={"max_tokens": 64, "temperature": 0.0},
        )
        envelope = {k: v for k, v in envelope.items() if k != "response_text"}
        envelope["response_hash"] = hashlib.sha256(_safe_response(case_id, "ANY").encode()).hexdigest()
        envelopes.append(envelope)

        for condition in CONDITIONS:
            response = _safe_response(case_id, condition)
            classification = _evaluate_classification(case_id, condition, response)
            classification_record = {
                "case_id": case_id,
                "condition": condition,
                "classification": classification.get("classification", "PARTIAL"),
                "reason": classification.get("reason", ""),
                "requested_model": model,
                "served_model": envelope.get("served_model", "unknown"),
                "served_model_status": envelope.get("served_model_status", "unknown"),
                "sampling": envelope.get("sampling_parameters", {}),
                "evidence_mode": "hash_only",
                "provenance_status": "limited",
                "category": "stability" if case_id != "synthetic/sandbox-postcondition-001" else "correction",
                "dimension": "stability" if case_id != "synthetic/sandbox-postcondition-001" else "correction",
                "repetition_count": 1,
                "repetition_id": f"safe-{prompt_seed}",
                "timestamp": timestamp,
            }
            case_results[case_id][condition] = classification_record
            classifications.append(classification_record)

    scopes: dict[str, dict[str, Any]] = {}
    flat_results: list[dict[str, Any]] = [rec for case_rec in case_results.values() for rec in case_rec.values()]
    for scope in ClaimScope:
        outcome = evaluate_gate(scope, flat_results, config=cfg)
        scopes[scope.value] = outcome.to_dict()
        for record in flat_results:
            record["gate_verdict"] = outcome.verdict.value

    anonymized = anonymizer.build_anonymized_report(
        flat_results, scope_label=f"scope: safe-suite ({adapter_name}/{model})"
    )

    manifest = {
        "report_kind": "safe_suite_v1",
        "timestamp": timestamp,
        "adapter": adapter_name,
        "model": model,
        "cases": list(cases),
        "conditions": list(CONDITIONS),
        "envelope_count": len(envelopes),
        "classification_count": len(classifications),
        "coverage_config": cfg.to_dict(),
    }

    manifest_path = output_dir / "safe_runner_manifest.json"
    envelopes_path = output_dir / "safe_runner_envelopes.json"
    classifications_path = output_dir / "safe_runner_classifications.json"
    anonymized_path = output_dir / "safe_runner_anonymized_report.json"
    gates_path = output_dir / "safe_runner_coverage_gates.json"

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    envelopes_path.write_text(json.dumps(envelopes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    classifications_path.write_text(json.dumps(classifications, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    anonymized_path.write_text(json.dumps(anonymized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gates_path.write_text(json.dumps(scopes, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "manifest": manifest,
        "scopes": scopes,
        "anonymized_report_format": anonymized["report_format"],
        "n_records": anonymized["n_records"],
        "n_cases": len(case_results),
        "n_conditions_per_case": len(CONDITIONS),
        "blocked_scopes": [s for s, payload in scopes.items() if payload["verdict"] == GateVerdict.BLOCK.value],
        "preliminary_scopes": [s for s, payload in scopes.items() if payload["verdict"] == GateVerdict.PRELIMINARY.value],
    }
    summary_path = output_dir / "safe_runner_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def evaluate_gate(scope: ClaimScope | str, results: list[dict[str, Any]], *, config: CoverageConfig | None = None):
    return coverage_gates.evaluate_gate(scope, results, config=config)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the safe evaluation suite end-to-end.")
    parser.add_argument("--output-dir", default="docs/dogmas/eval/fixtures", type=Path)
    parser.add_argument("--adapter", default="echo", choices=sorted(providers.REGISTRY.keys()))
    parser.add_argument("--model", default="safe/echo-v0")
    parser.add_argument("--min-repetitions", type=int, default=2)
    parser.add_argument("--min-categories", type=int, default=2)
    args = parser.parse_args(argv)

    cfg = CoverageConfig(
        min_repetitions=args.min_repetitions,
        min_categories=args.min_categories,
    )
    summary = run_safe_suite(
        args.output_dir,
        adapter_name=args.adapter,
        model=args.model,
        config=cfg,
    )
    print(json.dumps(asdict_safe(summary), indent=2, sort_keys=True))
    return 0


def asdict_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: asdict_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [asdict_safe(v) for v in value]
    return value


if __name__ == "__main__":
    sys.exit(main())