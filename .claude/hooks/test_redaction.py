"""Tests for the shared redactor and the PostToolUse redaction hook."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from redaction import redact, redact_obj

HOOK = Path(__file__).with_name("redact-output.py")


def test_json_quoted_password_is_redacted():
    text, types = redact('{"password": "hunter2hunter2"}')
    assert "hunter2hunter2" not in text
    assert "json_secret" in types


def test_json_quoted_aws_secret_is_redacted():
    text, types = redact('{"aws_secret_access_key": "abcd/efgh+ijkl/mnop+qrst/uvwx+yz01"}')
    assert "abcd/efgh" not in text
    assert "json_secret" in types


def test_connection_string_with_at_in_password_is_redacted():
    text, types = redact("postgres://user:S3cr3t@ss@db.internal/app")
    assert "S3cr3t" not in text
    assert "connection_string" in types


def test_entropy_secret_is_redacted():
    text, types = redact("api_key = " + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6")
    assert "A1b2C3d4" not in text
    assert "high_entropy_secret" in types


def test_nested_dict_secret_key_is_redacted():
    redacted, types = redact_obj({"credentials": {"password": "hunter2hunter2", "user": "u"}})
    assert redacted["credentials"]["password"] == "[REDACTED:secret_key]"
    assert redacted["credentials"]["user"] == "u"
    assert "secret_key" in types


def run_hook(payload: dict, tmp_path: Path) -> tuple[int, dict | None]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
    )
    output = json.loads(proc.stdout) if proc.stdout.strip() else None
    return proc.returncode, output


def test_stderr_only_secret_is_redacted(tmp_path):
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "psql"},
        "tool_response": {
            "stdout": "connection failed",
            "stderr": "could not connect: postgres://user:S3cr3t@db/app",
        },
    }
    code, output = run_hook(payload, tmp_path)
    assert code == 0
    assert output is not None
    updated = output["hookSpecificOutput"]["updatedToolOutput"]
    assert "S3cr3t" not in updated["stderr"]
    assert "S3cr3t" not in json.dumps(output)
    assert "connection_string" in output["hookSpecificOutput"]["additionalContext"]


def test_read_tool_content_is_redacted(tmp_path):
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/project/.env"},
        "tool_response": {"type": "text", "content": "AWS_SECRET_ACCESS_KEY=abcd/efgh+ijkl/mnop+qrst/uvwx+yz01"},
    }
    code, output = run_hook(payload, tmp_path)
    assert code == 0
    assert output is not None
    updated = output["hookSpecificOutput"]["updatedToolOutput"]
    assert "abcd/efgh" not in json.dumps(updated)
    assert updated["content"].startswith("AWS_SECRET_ACCESS_KEY=[REDACTED:")


def test_clean_output_is_untouched(tmp_path):
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "tool_response": {"stdout": "clean", "stderr": ""},
    }
    code, output = run_hook(payload, tmp_path)
    assert code == 0
    assert output is None


def test_failure_event_name_is_preserved(tmp_path):
    payload = {
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "psql"},
        "tool_response": {"stderr": "postgres://user:S3cr3t@db/app"},
    }
    code, output = run_hook(payload, tmp_path)
    assert code == 0
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"
    assert "S3cr3t" not in json.dumps(output)
