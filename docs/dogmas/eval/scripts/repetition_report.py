"""Generate a descriptive status report for the repetition registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

STATUSES = ("collected", "pending", "incomplete", "classified")


def classify_status(record: dict) -> str:
    status = record.get("status")
    if status == "classified":
        return "classified"
    if status == "incomplete":
        return "incomplete"
    if isinstance(record.get("response_literal"), str) and record["response_literal"].strip():
        return "collected"
    return "pending"


def build_report(registry: Path) -> dict:
    counts = Counter()
    by_case = Counter()
    by_model = Counter()
    records = []
    for path in sorted(registry.rglob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        status = classify_status(record)
        counts[status] += 1
        by_case[f"{record['case_id']}::{status}"] += 1
        by_model[f"{record['model']}::{status}"] += 1
        records.append({"path": str(path), "key": " + ".join(str(record.get(k)) for k in ("case_id", "model", "repetition_id", "condition")), "status": status})
    return {
        "schema_version": "manual-repetition-report-v1",
        "report_status": "preliminary_descriptive_only",
        "registry": str(registry),
        "total_records": sum(counts.values()),
        "counts": {status: counts[status] for status in STATUSES},
        "by_case": dict(sorted(by_case.items())),
        "by_model": dict(sorted(by_model.items())),
        "claims_supported": ["registry completeness and collection status", "descriptive classified observations when literal responses exist"],
        "claims_not_supported": ["statistical superiority", "causal effects", "equivalence", "global alignment", "memory promotion"],
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("docs/dogmas/eval/repetitions"))
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    report = build_report(args.registry)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
