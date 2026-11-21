#!/usr/bin/env python3
"""Merge the harness OpenCode config without dropping target-owned settings."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def strip_jsonc(text: str) -> str:
    """Remove JSONC comments and trailing commas while respecting strings."""
    out: list[str] = []
    i = 0
    quoted = False
    escaped = False
    while i < len(text):
        char = text[i]
        if quoted:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            i += 1
            continue
        if char == '"':
            quoted = True
            out.append(char)
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("unterminated JSONC block comment")
            i = end + 2
        else:
            out.append(char)
            i += 1
    cleaned = "".join(out)
    return re.sub(r",\s*([}\]])", r"\1", cleaned)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(strip_jsonc(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"config must be a JSON object: {path}")
    return value


def merge_config(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """Add missing defaults while preserving every target-owned setting.

    Ordered permission arrays and scalars are user-owned and kept verbatim.
    The ``instructions`` list is additive so the harness security policy is
    always presented; loading an instruction file never weakens permissions.
    Nested dicts are merged recursively with the same rules.
    """
    merged: dict[str, Any] = dict(source)
    for key, value in target.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(value, dict) and isinstance(merged[key], dict):
            merged[key] = merge_config(merged[key], value)
        elif key == "instructions" and isinstance(value, list) and isinstance(merged[key], list):
            merged[key] = value + [item for item in merged[key] if item not in value]
        else:
            merged[key] = value
    return merged


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: merge_opencode_config.py SOURCE TARGET", file=sys.stderr)
        return 2
    source_path, target_path = map(Path, args)
    merged = merge_config(load_config(source_path), load_config(target_path))
    target_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())