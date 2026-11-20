"""Tests for the settings merge used by the installer."""

from __future__ import annotations

from merge_settings import merge_settings


def test_target_only_keys_are_preserved():
    merged = merge_settings({"env": {"A": "1"}}, {"env": {"B": "2"}, "model": "sonnet"})
    assert merged["model"] == "sonnet"
    assert merged["env"] == {"B": "2"}


def test_permissions_are_unioned_without_duplicates():
    merged = merge_settings(
        {"permissions": {"allow": ["Read", "Grep"]}},
        {"permissions": {"allow": ["Read", "Bash(npm test)"]}},
    )
    assert merged["permissions"]["allow"] == ["Read", "Bash(npm test)", "Grep"]


def test_hooks_are_merged_by_matcher():
    merged = merge_settings(
        {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "guard.py"}]}
                ]
            }
        },
        {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "own.sh"}]}
                ]
            }
        },
    )
    commands = [
        hook["command"]
        for group in merged["hooks"]["PreToolUse"]
        for hook in group["hooks"]
    ]
    assert commands == ["own.sh", "guard.py"]


def test_duplicate_hook_command_is_not_added_twice():
    settings = {
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "scope.sh"}]}]
        }
    }
    merged = merge_settings(settings, settings)
    assert len(merged["hooks"]["Stop"][0]["hooks"]) == 1


def test_missing_event_is_added():
    merged = merge_settings(
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "stop.sh"}]}]}},
        {},
    )
    assert "Stop" in merged["hooks"]
