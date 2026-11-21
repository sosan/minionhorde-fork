from __future__ import annotations

import json
from pathlib import Path

from merge_opencode_config import load_config, merge_config, strip_jsonc


def test_strip_jsonc_keeps_comment_markers_inside_strings():
    text = '{"url":"https://example.test/a//b", // comment\n "enabled": true,}'
    assert json.loads(strip_jsonc(text)) == {
        "url": "https://example.test/a//b",
        "enabled": True,
    }

def test_merge_preserves_user_arrays_and_scalars():
    source = {
        "default_agent": "project-manager",
        "permissions": [{"action": "shell", "resource": "*", "effect": "ask"}],
        "plugins": ["./plugins/redact"],
    }
    target = {
        "default_agent": "build",
        "permissions": [{"action": "shell", "resource": "*", "effect": "deny"}],
        "plugins": ["user-plugin"],
    }
    merged = merge_config(source, target)
    assert merged == target


def test_merge_instructions_are_additive_but_deduplicated():
    source = {"instructions": [".opencode/rules/security-policy.md"]}
    target = {"instructions": ["CONTRIBUTING.md", ".opencode/rules/security-policy.md"]}
    merged = merge_config(source, target)
    assert merged["instructions"] == [
        "CONTRIBUTING.md",
        ".opencode/rules/security-policy.md",
    ]


def test_merge_recursively_adds_missing_defaults():
    source = {"experimental": {"todo": True, "subagent_depth": 2}, "default_agent": "project-manager"}
    target = {"experimental": {"todo": False, "custom": True}, "model": "provider/model"}
    assert merge_config(source, target) == {
        "experimental": {"todo": False, "subagent_depth": 2, "custom": True},
        "default_agent": "project-manager",
        "model": "provider/model",
    }


def test_merge_is_idempotent():
    source = {"permissions": [{"action": "external_directory", "resource": "*", "effect": "ask"}]}
    once = merge_config(source, {})
    assert merge_config(source, once) == once


def test_load_jsonc_file(tmp_path: Path):
    path = tmp_path / "opencode.jsonc"
    path.write_text('{\n // comment\n "default_agent": "project-manager",\n}\n', encoding="utf-8")
    assert load_config(path) == {"default_agent": "project-manager"}
