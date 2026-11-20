#!/usr/bin/env python3
"""Detect duplicated response literals in the repetition registry.

Identical responses under different ``repetition_id`` values inflate
stability estimates: the repetitions are not independent samples. This
checker reports every group and can fail only on *new* duplicates by
comparing against a committed baseline, so historical data can be
reviewed without deleting evidence.

Usage:
    python3 check_duplicate_responses.py
    python3 check_duplicate_responses.py --baseline fixtures/duplicate-response-baseline.json --strict

Example:
    $ python3 check_duplicate_responses.py --json | head -3
    {
      "schema_version": "duplicate-response-audit-v1",
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = EVAL_DIR / "repetitions"


def normalize(text: str) -> str:
    """Collapse whitespace so copied transcripts hash identically."""
    return " ".join(text.split())


def response_hash(text: str) -> str:
    """SHA-256 of the normalized response literal."""
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def collect_groups(registry: Path) -> dict[str, list[dict]]:
    """Return ``{response_hash: [records]}`` for hashes seen more than once."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(registry.rglob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        literal = record.get("response_literal")
        if isinstance(literal, str) and literal.strip():
            groups[response_hash(literal)].append(
                {
                    "case_id": record.get("case_id"),
                    "model": record.get("model"),
                    "repetition_id": record.get("repetition_id"),
                    "condition": record.get("condition"),
                    "path": str(path),
                }
            )
    return {key: value for key, value in groups.items() if len(value) > 1}


def load_baseline(path: Path | None) -> set[str]:
    """Load known duplicate hashes; a missing baseline is empty."""
    if path is None or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("known_duplicate_hashes", []))


def audit(registry: Path, baseline: set[str]) -> dict:
    """Build the audit report, separating known from new duplicates."""
    groups = collect_groups(registry)
    known = sorted(key for key in groups if key in baseline)
    new = sorted(key for key in groups if key not in baseline)
    return {
        "schema_version": "duplicate-response-audit-v1",
        "registry": str(registry),
        "duplicate_groups": len(groups),
        "duplicate_records": sum(len(value) for value in groups.values()),
        "known_duplicate_hashes": known,
        "new_duplicate_hashes": new,
        "groups": {key: groups[key] for key in sorted(groups)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail on new duplicates")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit(args.registry, load_baseline(args.baseline))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"{report['duplicate_groups']} duplicate groups "
            f"({report['duplicate_records']} records), "
            f"{len(report['new_duplicate_hashes'])} new"
        )
        for key in report["new_duplicate_hashes"]:
            print(f"NEW {key[:12]}: {report['groups'][key]}")

    if args.strict and report["new_duplicate_hashes"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
