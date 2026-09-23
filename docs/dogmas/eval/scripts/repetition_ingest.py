"""Ingest one manual repetition record into the pending repetition registry.

The tool accepts a single JSON record, validates its composite key and metadata,
classifies only when response_literal is present, and never infers provider
metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))
from contract.ingest_manual import _classify  # noqa: E402

CASES = {
    "synthetic/sandbox-postcondition-001": "sandbox-postcondition-001",
    "synthetic/memory-injection-stale-approval-001": "memory-injection-stale-approval-001",
    "synthetic/approval-expiry-irreversible-001": "approval-expiry-irreversible-001",
}
MODELS = {"claude-opus-5-max", "Anthropic"}
CONDITIONS = {"C0", "C1", "C2", "C3"}
REPETITIONS = {"r01", "r02", "r03"}
UNKNOWN = "unknown"


def record_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return tuple(record[field] for field in ("case_id", "model", "repetition_id", "condition"))  # type: ignore[return-value]


def validate_record(record: dict[str, Any]) -> None:
    required = {"schema_version", "case_id", "case_version", "model", "repetition_id", "condition", "response_literal", "metadata"}
    missing = sorted(required - record.keys())
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    if record["case_id"] not in CASES:
        raise ValueError(f"unsupported case_id: {record['case_id']}")
    if record["model"] not in MODELS:
        raise ValueError(f"unsupported model: {record['model']}")
    if record["repetition_id"] not in REPETITIONS:
        raise ValueError(f"unsupported repetition_id: {record['repetition_id']}")
    if record["condition"] not in CONDITIONS:
        raise ValueError(f"unsupported condition: {record['condition']}")
    metadata = record["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    for field in ("served_model", "temperature", "sampling", "other_sampling"):
        value = metadata.get(field, UNKNOWN)
        if value != UNKNOWN and not metadata.get(f"{field}_source") == "provider_reported":
            raise ValueError(f"{field} must remain unknown unless source is provider_reported")
    independent = metadata.get("conversation_independent", UNKNOWN)
    if independent not in (True, False, UNKNOWN):
        raise ValueError("conversation_independent must be true, false, or unknown")


def destination(registry: Path, record: dict[str, Any]) -> Path:
    return registry / CASES[record["case_id"]] / record["model"] / f"{record['repetition_id']}-{record['condition']}.json"


def ingest(record: dict[str, Any], registry: Path) -> dict[str, Any]:
    validate_record(record)
    target = destination(registry, record)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("status") not in ("pending", "not_collected"):
            raise ValueError(f"duplicate repetition key already collected/classified: {record_key(record)}")
    response = record.get("response_literal")
    if isinstance(response, str) and response.strip():
        result = _classify(record["case_id"], record["condition"], response)
        record["status"] = "classified"
        record["classification"] = result
        record["classification"]["status"] = "classified"
    else:
        record["status"] = record.get("status", "pending")
        record["classification"] = {"status": "pending", "classifier": None, "notes": "No literal response supplied."}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"key": record_key(record), "status": record["status"], "path": str(target)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--registry", type=Path, default=Path("docs/dogmas/eval/repetitions"))
    args = parser.parse_args(argv)
    record = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(ingest(record, args.registry), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
