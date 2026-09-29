"""Audit consistency and completeness of the manual evaluation closure."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVAL = ROOT / "docs/dogmas/eval"
REGISTRY = EVAL / "repetitions"
REPORT = EVAL / "fixtures/manual-vertical-slice-preliminary-report-v2.json"
ANALYSIS = EVAL / "fixtures/manual-descriptive-analysis-v2.json"
LIMITATIONS = EVAL / "LIMITATIONS.md"
STAT_OUTPUT = EVAL / "fixtures/statistical-analysis-output.txt"


def load_records() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in REGISTRY.rglob("*.json")]


def audit() -> dict:
    records = load_records()
    status_counts = Counter(r.get("status") for r in records)
    model_counts = Counter(r.get("model") for r in records)
    keys = [
        (r.get("case_id"), r.get("model"), r.get("repetition_id"), r.get("condition"))
        for r in records
    ]
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    missing_literal = sorted(
        key for key, r in zip(keys, records)
        if r.get("status") == "classified" and not isinstance(r.get("response_literal"), str)
    )
    unsupported_statuses = sorted(set(status_counts) - {"classified", "pending", "collected", "incomplete"})

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))

    checks = {
        "registry_total_72": len(records) == 72,
        "all_classified": status_counts == Counter({"classified": 72}),
        "models_balanced": model_counts == Counter({"Anthropic": 36, "claude-opus-5-max": 36}),
        "unique_composite_keys": not duplicate_keys,
        "classified_records_have_literal": not missing_literal,
        "no_unsupported_statuses": not unsupported_statuses,
        "report_status_preliminary": report.get("status") == "preliminary_descriptive_only",
        "analysis_status_preliminary": analysis.get("status") == "preliminary_descriptive_only",
        "report_has_limitations_reference": report.get("limitations_reference") == "docs/dogmas/eval/LIMITATIONS.md",
        "limitations_exists": LIMITATIONS.exists(),
        "statistical_output_exists": STAT_OUTPUT.exists(),
        "report_claims_not_supported_present": bool(report.get("claims_not_supported")),
    }

    return {
        "schema_version": "methodological-audit-v1",
        "audit_id": "manual-evaluation-closure-001",
        "status": "CLOSED_PRELIMINARY_DESCRIPTIVE_ONLY" if all(checks.values()) else "OPEN_REVIEW_REQUIRED",
        "checks": checks,
        "registry": {
            "total": len(records),
            "status_counts": dict(status_counts),
            "model_counts": dict(model_counts),
            "duplicate_keys": [list(key) for key in duplicate_keys],
            "classified_without_literal": [list(key) for key in missing_literal],
            "unsupported_statuses": unsupported_statuses,
        },
        "report": {
            "status": report.get("status"),
            "aggregate": report.get("aggregate"),
            "limitations_reference": report.get("limitations_reference"),
        },
        "analysis": {
            "status": analysis.get("status"),
            "evidence_scope": analysis.get("evidence_scope"),
        },
        "closure": {
            "manual_collection_frozen": True,
            "new_manual_tests_run": False,
            "claims_allowed": ["literal descriptive observations", "exploratory diagnostics"],
            "claims_forbidden": ["statistical superiority", "equivalence", "causal effects", "global alignment", "production safety certification"],
            "pending_data": "none in the declared 72-record registry",
            "known_scope_gap": "cases 01, 03, and 05 have no repetition series",
        },
    }


def main() -> int:
    result = audit()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "CLOSED_PRELIMINARY_DESCRIPTIVE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
