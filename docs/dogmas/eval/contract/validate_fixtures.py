#!/usr/bin/env python3
"""Validate fixtures in docs/dogmas/eval/fixtures/ against the v1 schemas.

Usage:
    python3 -m contract.validate_fixtures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.schema_store import SchemaStore, SchemaValidationError


def main() -> int:
    store = SchemaStore()
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    failures = 0
    checked = 0

    for path in sorted(fixtures_dir.glob("**/*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        relative = path.relative_to(fixtures_dir)
        parts = relative.parts
        checked += 1

        # Legacy records are intentionally outside the modern schema contract.
        if parts[0] == "legacy":
            expected = {
                "provenance_status": "legacy_limited",
                "classification_authority": "unverified",
                "served_model": "unknown",
                "evidence_mode": "summary",
            }
            ok = all(document.get(key) == value for key, value in expected.items())
            if not ok:
                failures += 1
                print(f"FAIL {relative}: invalid legacy-limited migration markers")
            else:
                print(f"ok   {relative} (legacy-limited)")
            continue

        schema_name = parts[1]
        is_valid = parts[0] == "valid"
        try:
            store.validate(schema_name, document)
            ok = True
        except SchemaValidationError:
            ok = False
        except FileNotFoundError as exc:
            failures += 1
            print(f"FAIL {relative}: {exc}")
            continue
        if ok != is_valid:
            failures += 1
            print(f"FAIL {relative}: expected valid={is_valid}, got {ok}")
        else:
            print(f"ok   {relative}")
    print(f"\n{checked} fixtures checked, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())