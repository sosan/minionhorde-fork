#!/usr/bin/env python3
"""Report Claude hook command, test, and CI/pre-commit coverage."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def command_path(command: str, root: Path) -> Path | None:
    match = re.search(r"(?:CLAUDE_PROJECT_DIR\}/|hooks/)([A-Za-z0-9_.-]+(?:\.py|\.sh))", command)
    return root / ".claude" / "hooks" / match.group(1) if match else None


def test_candidates(path: Path, root: Path) -> list[str]:
    stem = path.stem.replace("-", "_")
    candidates = sorted(root.glob(f"**/test_{stem}.py"))
    return [str(candidate.relative_to(root)) for candidate in candidates]


def report(root: Path) -> dict[str, Any]:
    settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
    ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    precommit_path = root / ".pre-commit-config.yaml"
    precommit = precommit_path.read_text(encoding="utf-8") if precommit_path.exists() else ""
    hooks: list[dict[str, Any]] = []
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command", "")
                path = command_path(command, root)
                hooks.append({
                    "event": event,
                    "matcher": group.get("matcher", "*"),
                    "command": command,
                    "implementation": str(path.relative_to(root)) if path and path.exists() else None,
                    "implementation_exists": bool(path and path.exists()),
                    "tests": test_candidates(path, root) if path and path.exists() else [],
                    "ci_reference": bool(path and path.name in ci),
                    "precommit_reference": bool(path and path.name in precommit),
                })
    return {"hooks": hooks, "summary": {
        "total": len(hooks),
        "missing_implementation": sum(not h["implementation_exists"] for h in hooks),
        "with_tests": sum(bool(h["tests"]) for h in hooks),
        "ci_referenced": sum(h["ci_reference"] for h in hooks),
        "precommit_referenced": sum(h["precommit_reference"] for h in hooks),
    }}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="fail if an implementation is missing")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = report(args.root.resolve())
    rendered = json.dumps(data, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if args.check and data["summary"]["missing_implementation"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
