from __future__ import annotations

import json
from pathlib import Path

import pytest

from validate_opencode_harness import (
    parse_frontmatter,
    project_agents_md_transform,
    validate,
    validate_agent,
    validate_template,
)

VALID_AGENT = """---
description: Test agent
mode: subagent
steps: 30
color: "#00d4ff"
permissions:
  - action: "*"
    resource: "*"
    effect: deny
  - action: read
    resource: "*"
    effect: allow
hidden: false
---

Body.
"""


def write_agent(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_frontmatter_scalars_and_list():
    parsed = parse_frontmatter(VALID_AGENT)
    assert parsed["mode"] == "subagent"
    assert parsed["steps"] == "30"
    assert parsed["color"] == "#00d4ff"
    assert parsed["permissions"][0] == {"action": "*", "resource": "*", "effect": "deny"}
    assert parsed["permissions"][1]["effect"] == "allow"


def test_parse_frontmatter_rejects_garbage():
    with pytest.raises(ValueError):
        parse_frontmatter("---\nnot yaml at all\n---\n")


def test_validate_agent_accepts_v2(tmp_path: Path):
    assert validate_agent(write_agent(tmp_path, "a.md", VALID_AGENT)) == []


def test_validate_agent_rejects_v1_keys(tmp_path: Path):
    text = VALID_AGENT.replace("hidden: false", "hidden: false\ntemperature: 0.3\npermission: allow")
    errors = validate_agent(write_agent(tmp_path, "a.md", text))
    assert any("V1-only keys" in e for e in errors)


def test_validate_agent_rejects_bad_mode_color_steps(tmp_path: Path):
    text = VALID_AGENT.replace("mode: subagent", "mode: wizard").replace('"#00d4ff"', '"red"').replace("steps: 30", "steps: -1")
    errors = validate_agent(write_agent(tmp_path, "a.md", text))
    assert any("mode" in e for e in errors)
    assert any("color" in e for e in errors)
    assert any("steps" in e for e in errors)


def test_validate_agent_rejects_bad_permission(tmp_path: Path):
    text = VALID_AGENT.replace('effect: allow', "effect: maybe")
    errors = validate_agent(write_agent(tmp_path, "a.md", text))
    assert any("effect" in e for e in errors)


def make_repo(root: Path) -> Path:
    (root / "agents").mkdir(parents=True)
    (root / "rules").mkdir()
    (root / "commands").mkdir()
    (root / "templates/context-files").mkdir(parents=True)
    (root / "templates/context-files/PRD.md").write_text("# PRD", encoding="utf-8")
    (root / "plugins/redact").mkdir(parents=True)
    (root / "plugins/redact/index.ts").write_text("//", encoding="utf-8")
    (root / "plugins/redact/package.json").write_text("{}", encoding="utf-8")
    (root / "rules/security-policy.md").write_text("# policy", encoding="utf-8")
    write_agent(root / "agents", "project-manager.md", VALID_AGENT.replace("mode: subagent", "mode: primary"))
    (root / "commands/build.md").write_text("---\ndescription: Build\n---\n\nDo the thing.\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("See `rules/security-policy.md` and `agents/project-manager.md`.\n", encoding="utf-8")
    project = {
        "default_agent": "project-manager",
        "instructions": [".opencode/rules/security-policy.md"],
        "experimental": {"todo": True, "subagent_depth": 2},
        "permissions": [{"action": "shell", "resource": "sudo *", "effect": "deny"}],
        "mcp": {"servers": {"memory": {"type": "local", "command": ["npx", "-y", "x"]}}},
        "plugins": ["./.opencode/plugins/redact"],
    }
    (root / "templates/opencode-project.json").write_text(json.dumps(project), encoding="utf-8")
    global_cfg = dict(project, instructions=["rules/security-policy.md"], plugins=["./plugins/redact"])
    (root / "templates/opencode-global.json").write_text(json.dumps(global_cfg), encoding="utf-8")
    return root


def test_validate_template_project_ok(tmp_path: Path):
    root = make_repo(tmp_path)
    assert validate_template(root / "templates/opencode-project.json", root, project=True) == []


def test_validate_template_global_ok(tmp_path: Path):
    root = make_repo(tmp_path)
    assert validate_template(root / "templates/opencode-global.json", root, project=False) == []


def test_validate_template_missing_instruction_source(tmp_path: Path):
    root = make_repo(tmp_path)
    config = json.loads((root / "templates/opencode-project.json").read_text(encoding="utf-8"))
    config["instructions"] = [".opencode/rules/nope.md"]
    (root / "templates/opencode-project.json").write_text(json.dumps(config), encoding="utf-8")
    errors = validate_template(root / "templates/opencode-project.json", root, project=True)
    assert any("nope.md" in e for e in errors)


def test_validate_template_missing_plugin(tmp_path: Path):
    root = make_repo(tmp_path)
    config = json.loads((root / "templates/opencode-global.json").read_text(encoding="utf-8"))
    config["plugins"] = ["./plugins/ghost"]
    (root / "templates/opencode-global.json").write_text(json.dumps(config), encoding="utf-8")
    errors = validate_template(root / "templates/opencode-global.json", root, project=False)
    assert any("ghost" in e for e in errors)


def test_validate_template_requires_todo_and_depth(tmp_path: Path):
    root = make_repo(tmp_path)
    config = json.loads((root / "templates/opencode-project.json").read_text(encoding="utf-8"))
    config["experimental"] = {"todo": False, "subagent_depth": 1}
    (root / "templates/opencode-project.json").write_text(json.dumps(config), encoding="utf-8")
    errors = validate_template(root / "templates/opencode-project.json", root, project=True)
    assert any("todo" in e for e in errors)
    assert any("subagent_depth" in e for e in errors)


def test_validate_full_repo_ok(tmp_path: Path):
    root = make_repo(tmp_path)
    report = validate(root)
    assert report["errors"] == []
    assert report["summary"]["valid"] is True
    assert report["summary"]["primary_agents"] == ["project-manager.md"]


def test_project_transform_rewrites_relative_but_keeps_global():
    text = "See `rules/security-policy.md`, `agents/test.md`, and `~/.config/opencode/agents/x.md` plus `.opencode/rules/y.md`.\n"
    out = project_agents_md_transform(text)
    assert "`.opencode/rules/security-policy.md`" in out
    assert "`.opencode/agents/test.md`" in out
    assert "`~/.config/opencode/agents/x.md`" in out
    assert "`.opencode/rules/y.md`" in out
