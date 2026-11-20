#!/usr/bin/env python3
"""Append-only JSON-lines audit log with a verifiable hash chain.

The old YAML-style log let a command containing newlines inject fake
entries and wrote the raw command (including secrets) to ``target``.
This module serializes each entry as one JSON object, redacts the
target, records the real status when the tool response is available,
rotates large logs, and chains every entry to the previous hash.

Usage:
    # PostToolUse hook (reads JSON from stdin)
    audit_log.py

    # Verify a log
    audit_log.py --verify .claude/audit/audit.log

Example:
    >>> append_entry(event="file_modified", tool="Write", target="src/a.py")
    {'schema_version': 'audit-v2', ...}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore[assignment]

from redaction import redact

SCHEMA_VERSION = "audit-v2"
MAX_BYTES = 1_000_000
MAX_ROTATED = 3


def _canonical(body: dict[str, Any]) -> str:
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _last_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and isinstance(entry.get("hash"), str):
            return entry["hash"]
    return ""


def _rotate(path: Path) -> None:
    if not path.exists() or path.stat().st_size < MAX_BYTES:
        return
    for index in range(MAX_ROTATED, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        target = path.with_name(f"{path.name}.{index + 1}")
        if source.exists() and index == MAX_ROTATED:
            source.unlink()
        elif source.exists():
            os.replace(source, target)
    os.replace(path, path.with_name(f"{path.name}.1"))


def append_entry(
    *,
    event: str,
    tool: str,
    target: str = "",
    status: str = "success",
    redacted_types: list[str] | None = None,
    project_dir: str | Path | None = None,
    path: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one redacted, hash-chained entry and return it.

    Example:
        >>> entry = append_entry(event="tool_executed", tool="Bash", target="git status")
        >>> entry["event"]
        'tool_executed'
    """
    root = Path(project_dir or os.environ.get("CLAUDE_PROJECT_DIR", "."))
    log_path = Path(path) if path else root / ".claude" / "audit" / "audit.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    safe_target, target_types = redact(target)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        "tool": tool,
        "target": safe_target,
        "status": status,
        "redacted_types": sorted(set(redacted_types or []) | set(target_types)),
    }
    if extra:
        safe_extra, extra_types = _redact_extra(extra)
        body["extra"] = safe_extra
        body["redacted_types"] = sorted(set(body["redacted_types"]) | set(extra_types))

    # The lock covers rotation, reading the previous hash, and the append, so
    # two concurrent hooks cannot fork the chain with the same prev_hash.
    lock_path = log_path.with_suffix(log_path.suffix + ".lock")
    with open(lock_path, "a", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            _rotate(log_path)
            body["prev_hash"] = _last_hash(log_path)
            body["hash"] = _hash(body)
            line = json.dumps(body, ensure_ascii=False) + "\n"
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return body


def _redact_extra(value: Any) -> tuple[Any, list[str]]:
    if isinstance(value, str):
        redacted, types = redact(value)
        return redacted, types
    if isinstance(value, list):
        result = []
        types: list[str] = []
        for item in value:
            redacted, found = _redact_extra(item)
            result.append(redacted)
            types.extend(found)
        return result, sorted(set(types))
    if isinstance(value, dict):
        result = {}
        types = []
        for key, item in value.items():
            redacted, found = _redact_extra(item)
            result[key] = redacted
            types.extend(found)
        return result, sorted(set(types))
    return value, []


def verify(path: str | Path) -> tuple[bool, list[str]]:
    """Verify the hash chain of a JSON-lines audit log.

    Example:
        >>> ok, errors = verify(".claude/audit/audit.log")
        >>> isinstance(ok, bool)
        True
    """
    log_path = Path(path)
    if not log_path.exists():
        return False, [f"{log_path}: missing"]
    errors: list[str] = []
    previous = ""
    for number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON ({exc})")
            continue
        if not isinstance(entry, dict):
            errors.append(f"line {number}: entry is not an object")
            continue
        expected = entry.get("hash")
        body = {key: value for key, value in entry.items() if key != "hash"}
        if expected != _hash(body):
            errors.append(f"line {number}: hash mismatch")
        if entry.get("prev_hash") != previous:
            errors.append(f"line {number}: broken chain (prev_hash)")
        previous = expected if isinstance(expected, str) else ""
    return not errors, errors


def _status_from_response(response: Any) -> str:
    if not isinstance(response, dict):
        return "success"
    if response.get("is_error") or response.get("error"):
        return "error"
    exit_code = response.get("exit_code")
    if isinstance(exit_code, int) and exit_code != 0:
        return "error"
    if response.get("interrupted"):
        return "interrupted"
    return "success"


def _event_for(tool: str, command: str) -> str:
    if tool == "Bash" and any(
        marker in command
        for marker in ("push --force", "reset --hard", "DROP TABLE", "DELETE FROM", "rm -rf", "sudo")
    ):
        return "irreversible_command"
    if tool in {"Write", "Edit", "MultiEdit"}:
        return "file_modified"
    return "tool_executed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", metavar="PATH", help="verify a JSON-lines audit log")
    parser.add_argument("--path", metavar="PATH", help="override the log path")
    args = parser.parse_args(argv)

    if args.verify:
        ok, errors = verify(args.verify)
        for error in errors:
            print(error, file=sys.stderr)
        print("AUDIT_CHAIN_OK" if ok else "AUDIT_CHAIN_FAIL")
        return 0 if ok else 1

    payload = sys.stdin.read()
    if not payload.strip():
        return 0
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return 0

    tool = data.get("tool_name", "unknown")
    tool_input = data.get("tool_input", {}) or {}
    response = data.get("tool_response", data.get("tool_result", {}))
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    target = (
        command
        if tool == "Bash"
        else tool_input.get("file_path", "")
        if isinstance(tool_input, dict)
        else ""
    )
    append_entry(
        event=_event_for(tool, command),
        tool=tool,
        target=target,
        status=(
            "error"
            if data.get("hook_event_name") == "PostToolUseFailure"
            else _status_from_response(response)
        ),
        project_dir=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        path=args.path,
        extra={"session_id": data.get("session_id")} if data.get("session_id") else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
