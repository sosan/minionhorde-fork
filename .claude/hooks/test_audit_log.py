"""Tests for the JSON-lines, hash-chained audit log."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from audit_log import append_entry, verify

HOOK = Path(__file__).with_name("audit_log.py")


def test_newline_command_does_not_break_the_log(tmp_path):
    log = tmp_path / "audit.log"
    append_entry(
        event="tool_executed",
        tool="Bash",
        target="echo one\necho two",
        path=log,
    )
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["target"] == "echo one\necho two"


def test_target_secret_is_redacted(tmp_path):
    log = tmp_path / "audit.log"
    entry = append_entry(
        event="tool_executed",
        tool="Bash",
        target="curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz'",
        path=log,
    )
    assert "abcdefghijklmnopqrstuvwxyz" not in json.dumps(entry)
    assert "authorization_header" in entry["redacted_types"]


def test_hash_chain_verifies_and_detects_tampering(tmp_path):
    log = tmp_path / "audit.log"
    append_entry(event="tool_executed", tool="Bash", target="git status", path=log)
    append_entry(event="file_modified", tool="Write", target="src/a.py", path=log)
    ok, errors = verify(log)
    assert ok, errors

    lines = log.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[1])
    entry["target"] = "tampered"
    lines[1] = json.dumps(entry)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, errors = verify(log)
    assert not ok
    assert any("hash mismatch" in error for error in errors)


def test_concurrent_appends_keep_one_chain(tmp_path):
    log = tmp_path / "audit.log"
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from audit_log import append_entry;"
        "append_entry(event='tool_executed', tool='Bash', target='echo', path=sys.argv[2])"
    )
    processes = [
        subprocess.Popen([sys.executable, "-c", script, str(HOOK.parent), str(log)])
        for _ in range(8)
    ]
    assert all(process.wait() == 0 for process in processes)
    assert len(log.read_text(encoding="utf-8").splitlines()) == 8
    ok, errors = verify(log)
    assert ok, errors


def test_cli_records_error_status(tmp_path):
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "false"},
        "tool_response": {"exit_code": 1, "stdout": "", "stderr": "failed"},
    }
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
    )
    assert proc.returncode == 0
    entry = json.loads((tmp_path / ".claude" / "audit" / "audit.log").read_text())
    assert entry["status"] == "error"


def test_cli_records_failure_event_as_error(tmp_path):
    payload = {
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "psql"},
        "tool_response": {"stderr": "connection refused"},
    }
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    entry = json.loads((tmp_path / ".claude" / "audit" / "audit.log").read_text())
    assert entry["status"] == "error"
