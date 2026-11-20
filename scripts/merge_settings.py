#!/usr/bin/env python3
"""Merge a harness settings.json into an existing project settings.json.

The installer must not overwrite a project's hooks, permissions, or
machine-specific configuration. This merge keeps the target values and
adds the harness values:

* ``permissions.allow`` and ``permissions.deny`` are de-duplicated unions.
* ``hooks`` are merged by event and matcher; hooks with the same
  ``command`` are not duplicated.
* Any other key from the source wins only when the target lacks it.

Example:
    $ merge_settings.py source.json target.json
    $ python3 -c 'import json; print(json.load(open("target.json"))["hooks"].keys())'
    dict_keys(['PreToolUse', 'PostToolUse', 'Stop'])
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _union(left: list[Any], right: list[Any]) -> list[Any]:
    result = list(left)
    for item in right:
        if item not in result:
            result.append(item)
    return result


def _merge_hook_group(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    merged.update({key: value for key, value in right.items() if key != "hooks"})
    commands = [hook.get("command") for hook in left.get("hooks", []) if isinstance(hook, dict)]
    hooks = list(left.get("hooks", []))
    for hook in right.get("hooks", []):
        if not isinstance(hook, dict) or hook.get("command") not in commands:
            hooks.append(hook)
    merged["hooks"] = hooks
    return merged


def merge_settings(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """Return a merged settings object without mutating either input.

    Example:
        >>> merge_settings({"permissions": {"allow": ["Read"]}}, {"permissions": {"allow": ["Bash"]}})["permissions"]["allow"]
        ['Bash', 'Read']
    """
    merged: dict[str, Any] = dict(target)
    for key, value in source.items():
        if key not in merged:
            merged[key] = value

    source_permissions = source.get("permissions", {}) or {}
    target_permissions = target.get("permissions", {}) or {}
    permissions = dict(target_permissions)
    for key, value in source_permissions.items():
        if isinstance(value, list) and isinstance(permissions.get(key), list):
            permissions[key] = _union(permissions[key], value)
        elif key not in permissions:
            permissions[key] = value
    merged["permissions"] = permissions

    hooks: dict[str, Any] = {}
    for event in set(source.get("hooks", {})) | set(target.get("hooks", {})):
        source_groups = (source.get("hooks", {}) or {}).get(event, []) or []
        target_groups = (target.get("hooks", {}) or {}).get(event, []) or []
        groups = list(target_groups)
        for source_group in source_groups:
            matcher = source_group.get("matcher")
            existing = next(
                (group for group in groups if group.get("matcher") == matcher),
                None,
            )
            if existing is None:
                groups.append(source_group)
            else:
                groups[groups.index(existing)] = _merge_hook_group(existing, source_group)
        hooks[event] = groups
    if hooks:
        merged["hooks"] = hooks
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)

    source = json.loads(args.source.read_text(encoding="utf-8"))
    target: dict[str, Any] = {}
    if args.target.exists() and args.target.stat().st_size > 0:
        target = json.loads(args.target.read_text(encoding="utf-8"))
    merged = merge_settings(source, target)
    args.target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
