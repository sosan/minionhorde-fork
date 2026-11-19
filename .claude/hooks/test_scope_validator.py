"""Tests for the Stop-hook heartbeat gate (C3).

Runs `.claude/hooks/scope-validator.sh` as a subprocess with simulated
UserPromptSubmit JSON on stdin and isolated counter/audit paths, so the tests
never touch the repository audit files.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).with_name("scope-validator.sh")


def run_hook(message: str, tmp_path: Path, retries: int = 0) -> tuple[int, str, Path, Path]:
    counter = tmp_path / "counter"
    audit = tmp_path / "audit.log"
    env = {
        **os.environ,
        "CLAUDE_HEARTBEAT_COUNTER_FILE": str(counter),
        "CLAUDE_HEARTBEAT_AUDIT_FILE": str(audit),
    }
    payload = json.dumps({"last_assistant_message": message})
    proc = subprocess.run(
        [str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    return proc.returncode, proc.stdout, counter, audit


def test_short_ack_passes(tmp_path):
    code, out, counter, _ = run_hook("ok", tmp_path)
    assert code == 0
    assert out == ""
    assert not counter.exists()


def test_factual_list_passes_without_heartbeat(tmp_path):
    msg = "\n".join(f"file {i}" for i in range(5))
    code, out, _, _ = run_hook(msg, tmp_path)
    assert code == 0
    assert out == ""


def test_decision_without_heartbeat_blocks(tmp_path):
    code, out, counter, _ = run_hook("I recommend merging this branch.", tmp_path)
    assert code == 2
    assert "CORE Inv 16" in out
    assert counter.read_text().strip() == "1"


def test_scope_without_security_blocks(tmp_path):
    msg = "I recommend merging.\nScope: complete."
    code, out, counter, _ = run_hook(msg, tmp_path)
    assert code == 2
    assert "Security:" in out
    assert counter.exists()


def test_complete_heartbeat_passes_and_resets(tmp_path):
    msg = "I recommend merging.\nScope: complete.\nSecurity: nothing to declare."
    counter = tmp_path / "counter"
    counter.write_text("1")
    code, out, counter_after, _ = run_hook(msg, tmp_path)
    assert code == 0
    assert out == ""
    assert not counter_after.exists()


def test_retry_sequence_blocks_twice_then_warns(tmp_path):
    counter = tmp_path / "counter"
    audit = tmp_path / "audit.log"
    env = {
        **os.environ,
        "CLAUDE_HEARTBEAT_COUNTER_FILE": str(counter),
        "CLAUDE_HEARTBEAT_AUDIT_FILE": str(audit),
    }
    payload = json.dumps({"last_assistant_message": "I recommend merging."})
    results = []
    for _ in range(3):
        proc = subprocess.run(
            [str(HOOK)], input=payload, text=True, capture_output=True, env=env
        )
        results.append(proc.returncode)
    assert results == [2, 2, 0]
    assert not counter.exists()
    assert "heartbeat_missing_after_retries" in audit.read_text()


def test_empty_message_passes(tmp_path):
    code, out, counter, _ = run_hook("", tmp_path)
    assert code == 0
    assert out == ""
    assert not counter.exists()