#!/usr/bin/env python3
"""Normalizes case_id positionally in all JSON files.

Assumption: 25-item files cover cases 6-30 (appendixD) in the same order,
and 5-item files cover cases 1-5 (canonicals) in the same order.

Replaces all case_ids with case-01..case-05 or case-06..case-30 by size.

Usage:
    python3 eval/normalize_case_ids.py
    python3 eval/normalize_case_ids.py --dry-run  # only shows changes
"""
import json
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def main():
    dry_run = "--dry-run" in sys.argv
    files = sorted(RESULTS_DIR.glob("*.json"))

    for path in files:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, list):
            continue

        n = len(data)
        if n == 5:
            # Canonical cases: case-01..case-05
            for idx, item in enumerate(data):
                new_id = f"case-{idx+1:02d}"
                old_id = item.get("case_id", "")
                if old_id != new_id:
                    print(f"{path.name}[{idx}]: {old_id} -> {new_id}")
                    if not dry_run:
                        item["case_id"] = new_id
        elif n == 25:
            # appendixD cases: case-06..case-30
            for idx, item in enumerate(data):
                new_id = f"case-{idx+6:02d}"
                old_id = item.get("case_id", "")
                if old_id != new_id:
                    print(f"{path.name}[{idx}]: {old_id} -> {new_id}")
                    if not dry_run:
                        item["case_id"] = new_id
        else:
            print(f"ADVERTENCIA: {path.name} tiene {n} items (esperado 5 o 25), se omite")
            continue

        if not dry_run:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print()
    print("Modo:", "DRY-RUN (no se escribio nada)" if dry_run else "APLICADO")


if __name__ == "__main__":
    main()
