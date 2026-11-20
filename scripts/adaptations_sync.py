#!/usr/bin/env python3
"""Sync-check the Claude Code agent adaptations against their OpenCode SSOT.

The `.claude/agents/*.md` files are manual adaptations of `agents/*.md`
(OpenCode). Their bodies legitimately diverge (tool names, permission model,
protocol text), so this tool does NOT regenerate bodies. It owns the one part
that must stay identical: the Claude-side metadata frontmatter (name,
description, model, tools) is defined once here and compared/updated against
the files.

Modes:
    --check                 (default) verify metadata parity; exit 1 on drift
    --update                rewrite the frontmatter of .claude/agents/*.md
                            from the canonical map; body is never touched
    --workflow              verify the workflow adaptation header/sections

Usage:
    python3 scripts/adaptations_sync.py --check
    python3 scripts/adaptations_sync.py --update
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())

VALID_MODELS = {"sonnet", "opus", "haiku", "inherit"}
VALID_TOOLS = {
    "Read", "Glob", "Grep", "Write", "Edit", "Bash", "Agent",
    "TodoWrite", "WebSearch", "WebFetch", "AskUserQuestion",
}

# Canonical Claude-side metadata. source = OpenCode SSOT under agents/.
AGENTS: dict[str, dict[str, object]] = {
    "architect": {
        "source": "agents/architect.md",
        "description": "Architect Agent — technical planning support role (tandem with Project Manager), tier-aware",
        "tools": ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "TodoWrite"],
        "model": "sonnet",
    },
    "code-review": {
        "source": "agents/code-review.md",
        "description": "Code Review Agent — tier-aware quality review, security analysis, incident categorization",
        "tools": ["Read", "Glob", "Grep", "TodoWrite"],
        "model": "sonnet",
    },
    "developer": {
        "source": "agents/developer.md",
        "description": "Developer Agent — tier-aware implementation (new project, feature, bug fix) with on-demand skills",
        "tools": ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "TodoWrite", "WebSearch", "WebFetch"],
        "model": "opus",
    },
    "devops": {
        "source": "agents/devops.md",
        "description": "DevOps Agent — tier-aware CI/CD, deployment, Git operations, changelog",
        "tools": ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "TodoWrite"],
        "model": "opus",
    },
    "documentation": {
        "source": "agents/documentation.md",
        "description": "Documentation Agent — docs maintenance, specs sync, on-demand reports",
        "tools": ["Read", "Glob", "Grep", "Write", "Edit", "TodoWrite"],
        "model": "sonnet",
    },
    "project-manager": {
        "source": "agents/project-manager.md",
        "description": "Project Manager — workflow coordinator, tier detection, phase gates, delegation",
        "tools": ["Read", "Glob", "Grep", "Agent", "TodoWrite", "WebSearch", "WebFetch"],
        "model": "sonnet",
    },
    "test": {
        "source": "agents/test.md",
        "description": "Test Agent — TDD stubs, test execution, regression coverage, pass/fail reports",
        "tools": ["Read", "Glob", "Grep", "Write", "Bash", "TodoWrite"],
        "model": "opus",
    },
}

WORKFLOW_PAIRS = [
    ("rules/workflow-protocols.md", ".claude/rules/workflow.md"),
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract the YAML-ish frontmatter between leading --- markers."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    block = text[3:end]
    # `end` points at the newline before the closing marker; the newline that
    # terminates the closing `---` line belongs to the frontmatter block because
    # render_frontmatter() re-emits it. It must not end up in the body, or every
    # --update run would accumulate one blank line (old bug).
    body_start = end + 5 if text.startswith("\n", end + 4) else end + 4
    body = text[body_start:]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body


def render_frontmatter(meta: dict[str, object]) -> str:
    lines = ["---", f"name: {meta['name']}"]
    tools = ", ".join(meta["tools"])
    lines.append(f"description: {meta['description']}")
    lines.append(f"tools: [{tools}]")
    lines.append(f"model: {meta['model']}")
    return "\n".join(lines) + "\n---\n"


def check_one(name: str, meta: dict[str, object]) -> list[str]:
    errors: list[str] = []
    claude = REPO_ROOT / ".claude" / "agents" / f"{name}.md"
    ssot = REPO_ROOT / str(meta["source"])
    if not claude.exists():
        return [f"{name}: .claude/agents/{name}.md missing"]
    if not ssot.exists():
        errors.append(f"{name}: SSOT {meta['source']} missing")
    meta_with_name = {"name": name, **meta}
    fields, _body = parse_frontmatter(claude.read_text(encoding="utf-8"))
    if fields.get("name") != name:
        errors.append(f"{name}: frontmatter name is {fields.get('name')!r}, expected {name!r}")
    if fields.get("description") != meta["description"]:
        errors.append(f"{name}: description drifted")
    if fields.get("model") != meta["model"]:
        errors.append(f"{name}: model is {fields.get('model')!r}, expected {meta['model']!r}")
    declared = fields.get("tools", "")
    expected = f"[{', '.join(meta['tools'])}]"
    if declared != expected:
        errors.append(f"{name}: tools are {declared!r}, expected {expected!r}")
    for tool in meta["tools"]:
        if tool not in VALID_TOOLS:
            errors.append(f"{name}: unknown tool {tool!r}")
    if meta["model"] not in VALID_MODELS:
        errors.append(f"{name}: unknown model {meta['model']!r}")
    return errors


def update_one(name: str, meta: dict[str, object]) -> tuple[bool, str]:
    path = REPO_ROOT / ".claude" / "agents" / f"{name}.md"
    if not path.exists():
        return False, f"{name}: missing, nothing to update"
    text = path.read_text(encoding="utf-8")
    _fields, body = parse_frontmatter(text)
    meta_with_name = {"name": name, **meta}
    new_text = render_frontmatter(meta_with_name) + body
    if new_text == text:
        return False, f"{name}: already in sync"
    path.write_text(new_text, encoding="utf-8")
    return True, f"{name}: frontmatter updated (body untouched)"


def check_workflow() -> list[str]:
    errors: list[str] = []
    for ssot_rel, claude_rel in WORKFLOW_PAIRS:
        ssot = REPO_ROOT / ssot_rel
        claude = REPO_ROOT / claude_rel
        if not ssot.exists():
            errors.append(f"workflow: SSOT {ssot_rel} missing")
        if not claude.exists():
            errors.append(f"workflow: adaptation {claude_rel} missing")
            continue
        text = claude.read_text(encoding="utf-8")
        if "adaptation" not in text.lower() or "source of truth" not in text.lower():
            errors.append(f"workflow: {claude_rel} lacks the adaptation header")
        for marker in ("## TDD Protocol", "## Rollback Protocol"):
            if marker not in text:
                errors.append(f"workflow: {claude_rel} missing {marker}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="verify parity (default)")
    group.add_argument("--update", action="store_true", help="rewrite frontmatter from canonical map")
    group.add_argument("--workflow", action="store_true", help="verify workflow adaptation headers")
    args = parser.parse_args(argv)

    if args.update:
        changed = 0
        for name, meta in AGENTS.items():
            did, msg = update_one(name, meta)
            changed += did
            print(msg)
        print(f"update complete: {changed} file(s) written")
        return 0

    if args.workflow:
        errors = check_workflow()
        for err in errors:
            print(f"FAIL {err}")
        return 1 if errors else 0

    # default: --check
    errors: list[str] = []
    for name, meta in AGENTS.items():
        errors.extend(check_one(name, meta))
    errors.extend(check_workflow())
    for err in errors:
        print(f"FAIL {err}")
    if not errors:
        print("OK: all agent adaptations and workflow headers in sync")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())