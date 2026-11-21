#!/usr/bin/env python3
"""Validate the OpenCode V2 harness sources before install or CI.

Checks, with zero third-party dependencies:
- ``agents/*.md`` frontmatter uses only V2-native keys (no V1 leftovers such as
  ``temperature``, ``permission``, ``tools``, ``disable``, ``maxSteps``) and
  well-formed values (mode, hex color, positive steps, permission rules).
- ``templates/opencode-*.json`` parse, point ``default_agent`` at an existing
  primary agent, enable ``experimental.todo``/``subagent_depth``, and reference
  only instruction files and plugins that exist in this repo.
- ``commands/*.md`` have a description and a non-empty body.
- ``AGENTS.md`` survives the project-install sed: after rewriting relative
  ``rules/``/``agents/`` references to ``.opencode/...``, no bare reference
  remains and no ``~/.config/opencode/rules/`` path leaks into a project.

Exit codes: 0 = valid; 1 = validation errors; 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

V2_AGENT_KEYS = {"description", "mode", "model", "steps", "color", "hidden", "disabled", "permissions", "request"}
V1_ONLY_KEYS = {"temperature", "top_p", "prompt", "permission", "tools", "disable", "maxSteps"}
MODES = {"primary", "subagent", "all"}
EFFECTS = {"allow", "ask", "deny"}
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
RULE_KEYS = {"action", "resource", "effect"}


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the strict frontmatter subset used by this repo's markdown files.

    Supports ``key: value`` scalars and ``key:`` followed by a list of
    ``- key: value`` items with indented continuation keys. Anything else
    raises ValueError — strictness is the point of validation.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening ---")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("missing closing ---")
    body = lines[1:end]
    result: dict[str, Any] = {}
    i = 0
    while i < len(body):
        line = body[i]
        if not line.strip():
            i += 1
            continue
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not match:
            raise ValueError(f"unparseable frontmatter line: {line!r}")
        key, value = match.group(1), match.group(2).strip()
        if value:
            result[key] = value.strip('"')
            i += 1
            continue
        items: list[dict[str, str]] = []
        i += 1
        while i < len(body) and body[i].startswith("  "):
            stripped = body[i].strip()
            if stripped.startswith("- "):
                items.append({})
                stripped = stripped[2:]
            if not items:
                raise ValueError(f"continuation without list item under {key!r}")
            k, _, v = stripped.partition(":")
            items[-1][k.strip()] = v.strip().strip('"')
            i += 1
        result[key] = items
    return result


def validate_agent(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{path.name}: {exc}"]
    unknown = set(frontmatter) - V2_AGENT_KEYS
    legacy = set(frontmatter) & V1_ONLY_KEYS
    if unknown:
        errors.append(f"{path.name}: unknown frontmatter keys: {sorted(unknown)}")
    if legacy:
        errors.append(f"{path.name}: V1-only keys must be removed: {sorted(legacy)}")
    if not frontmatter.get("description"):
        errors.append(f"{path.name}: description is required")
    mode = frontmatter.get("mode")
    if mode not in MODES:
        errors.append(f"{path.name}: mode must be one of {sorted(MODES)}, got {mode!r}")
    color = frontmatter.get("color")
    if color is not None and not COLOR_RE.match(str(color)):
        errors.append(f"{path.name}: color must be a six-digit hex value, got {color!r}")
    steps = frontmatter.get("steps")
    if steps is not None and (not str(steps).isdigit() or int(steps) <= 0):
        errors.append(f"{path.name}: steps must be a positive integer, got {steps!r}")
    for flag in ("hidden", "disabled"):
        if flag in frontmatter and frontmatter[flag] not in ("true", "false"):
            errors.append(f"{path.name}: {flag} must be true/false, got {frontmatter[flag]!r}")
    permissions = frontmatter.get("permissions", [])
    if not isinstance(permissions, list):
        errors.append(f"{path.name}: permissions must be a list")
    else:
        for index, rule in enumerate(permissions):
            if not isinstance(rule, dict) or set(rule) - RULE_KEYS or not {"action", "resource", "effect"} <= set(rule):
                errors.append(f"{path.name}: permissions[{index}] must have exactly action/resource/effect: {rule!r}")
                continue
            if rule["effect"] not in EFFECTS:
                errors.append(f"{path.name}: permissions[{index}].effect must be allow/ask/deny, got {rule['effect']!r}")
    return errors


def validate_template(path: Path, root: Path, project: bool) -> list[str]:
    errors: list[str] = []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"{path.name}: invalid JSON: {exc}"]
    default_agent = config.get("default_agent")
    agent_file = root / "agents" / f"{default_agent}.md"
    if not default_agent or not agent_file.exists():
        errors.append(f"{path.name}: default_agent {default_agent!r} has no agents/{default_agent}.md")
    else:
        frontmatter = parse_frontmatter(agent_file.read_text(encoding="utf-8"))
        if frontmatter.get("mode") != "primary":
            errors.append(f"{path.name}: default_agent {default_agent!r} must be mode: primary")
    experimental = config.get("experimental", {})
    if experimental.get("todo") is not True:
        errors.append(f"{path.name}: experimental.todo must be true (todowrite tool)")
    if not isinstance(experimental.get("subagent_depth"), int) or experimental["subagent_depth"] < 2:
        errors.append(f"{path.name}: experimental.subagent_depth must be >= 2 (nested delegation)")
    permissions = config.get("permissions", [])
    for index, rule in enumerate(permissions):
        if not isinstance(rule, dict) or set(rule) != RULE_KEYS or rule.get("effect") not in EFFECTS:
            errors.append(f"{path.name}: permissions[{index}] malformed: {rule!r}")
    prefix = ".opencode/" if project else ""
    for instruction in config.get("instructions", []):
        if project:
            if not instruction.startswith(".opencode/"):
                errors.append(f"{path.name}: project instruction {instruction!r} must start with .opencode/")
                continue
            source = root / instruction[len(".opencode/"):]
        else:
            source = root / instruction
        if not source.exists():
            errors.append(f"{path.name}: instruction {instruction!r} has no source file {source.relative_to(root)}")
    plugin_prefix = "./.opencode/plugins/" if project else "./plugins/"
    for plugin in config.get("plugins", []):
        if not plugin.startswith(plugin_prefix):
            errors.append(f"{path.name}: plugin {plugin!r} must start with {plugin_prefix}")
            continue
        plugin_dir = root / "plugins" / plugin[len(plugin_prefix):]
        if not (plugin_dir / "index.ts").exists() or not (plugin_dir / "package.json").exists():
            errors.append(f"{path.name}: plugin {plugin!r} missing index.ts/package.json in plugins/")
    if "memory" not in config.get("mcp", {}).get("servers", {}):
        errors.append(f"{path.name}: mcp.servers.memory is required by the workflow")
    return errors


def validate_command(path: Path) -> list[str]:
    try:
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{path.name}: {exc}"]
    errors = []
    if not frontmatter.get("description"):
        errors.append(f"{path.name}: description is required")
    body = path.read_text(encoding="utf-8").split("---")
    if len(body) < 3 or not body[2].strip():
        errors.append(f"{path.name}: body (prompt template) is empty")
    return errors


def project_agents_md_transform(text: str) -> str:
    """Mirror the install.sh sed that rewrites relative paths for project installs."""
    text = re.sub(r"([^/])rules/", r"\1.opencode/rules/", text)
    text = re.sub(r"^rules/", ".opencode/rules/", text, flags=re.M)
    text = re.sub(r"([^/])agents/", r"\1.opencode/agents/", text)
    text = re.sub(r"^agents/", ".opencode/agents/", text, flags=re.M)
    return text


def validate_agents_md(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if "~/.config/opencode/rules/" in text:
        return ["AGENTS.md: literal ~/.config/opencode/rules/ path breaks the project sed"]
    transformed = project_agents_md_transform(text)
    errors = []
    for match in re.finditer(r"(?<!opencode/)(?<!\w)rules/", transformed):
        errors.append(f"AGENTS.md: bare rules/ reference survives project transform near {transformed[max(0, match.start() - 30):match.end() + 20]!r}")
    return errors


def validate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    agents = sorted((root / "agents").glob("*.md"))
    for agent in agents:
        errors.extend(validate_agent(agent))
    primaries = [
        a.name for a in agents
        if "mode" in parse_frontmatter(a.read_text(encoding="utf-8"))
        and parse_frontmatter(a.read_text(encoding="utf-8")).get("mode") == "primary"
    ]
    if not primaries:
        errors.append("agents/: no primary agent found (project-manager must be primary)")
    errors.extend(validate_template(root / "templates/opencode-project.json", root, project=True))
    errors.extend(validate_template(root / "templates/opencode-global.json", root, project=False))
    for command in sorted((root / "commands").glob("*.md")):
        errors.extend(validate_command(command))
    errors.extend(validate_agents_md(root / "AGENTS.md"))
    if not (root / "templates/context-files/PRD.md").exists():
        errors.append("templates/context-files/PRD.md missing (agent bodies reference it)")
    return {
        "errors": errors,
        "summary": {
            "agents": len(agents),
            "primary_agents": primaries,
            "commands": len(list((root / "commands").glob("*.md"))),
            "valid": not errors,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="exit 1 when validation errors exist")
    args = parser.parse_args(argv)
    report = validate(args.root.resolve())
    print(json.dumps(report, indent=2))
    return 1 if args.check and report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
