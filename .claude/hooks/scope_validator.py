#!/usr/bin/env python3
"""Stop-hook heartbeat gate.

Blocks a substantive response that lacks ``Scope:`` / ``Security:`` and
degrades to a warning after two blocks so the session cannot loop forever.

Improvements over the previous shell version:

* the retry counter is locked with ``fcntl.flock``, which the kernel releases
  when the process dies, so ``kill -9`` cannot leave a stale lock;
* the counter is per session, not global;
* the classifier uses word boundaries and a narrower vocabulary, so prose
  such as "the impact is limited" no longer triggers the gate.

Example:
    $ echo '{"last_assistant_message":"I recommend merging."}' | scope_validator.py
    {"decision": "block", "reason": "CORE Inv 16: ..."}
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from audit_log import append_entry

MAX_ATTEMPTS = 2

# One strong decision/risk signal is enough.
SIGNAL_RE = re.compile(
    r"\b(decision|decidi[oó]|decidir|trade-?off|reversib\w*|preflight|"
    r"irreversible|alternativa|alternative|riesgo|risk|recomiendo|recommend|"
    r"propongo|propose|sugiero|suggest|aprobado|approved|rechazado|rejected)\b",
    re.IGNORECASE,
)
CONNECTIVE_RE = re.compile(
    r"\b(because|therefore|porque|ya que|debido a|dado que|as a result)\b",
    re.IGNORECASE,
)


def is_substantive(message: str) -> bool:
    """Return whether a message is substantive enough to require a heartbeat.

    Example:
        >>> is_substantive("The impact is limited to the parser.")
        False
        >>> is_substantive("I recommend merging this branch.")
        True
    """
    lines = [line for line in message.splitlines() if line.strip()]
    if any(line.startswith(("Scope:", "Security:")) for line in lines):
        return True
    if SIGNAL_RE.search(message):
        return True
    return len(lines) >= 8 and bool(CONNECTIVE_RE.search(message))


def counter_path(project_dir: Path, session_id: str) -> Path:
    override = os.environ.get("CLAUDE_HEARTBEAT_COUNTER_FILE")
    if override:
        return Path(override)
    suffix = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:8] if session_id else "global"
    return project_dir / ".claude" / "audit" / f"heartbeat-retry.{suffix}.counter"


def read_attempt(counter: Path) -> int:
    try:
        value = counter.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    return int(value) if value.isdigit() else 0


def record_failure(audit: Path, project_dir: Path, missing: str) -> None:
    append_entry(
        event="heartbeat_missing_after_retries",
        tool="Stop",
        target=missing,
        status="warning",
        project_dir=project_dir,
        path=audit,
    )


def block(missing: str, attempt: int) -> int:
    output = {
        "decision": "block",
        "reason": (
            f"CORE Inv 16: substantive response missing {missing} "
            f"(attempt {attempt}/{MAX_ATTEMPTS})"
        ),
    }
    print(json.dumps(output))
    print(
        f"BLOCK: CORE Inv 16 requires {missing} (attempt {attempt}/{MAX_ATTEMPTS}).",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    payload = sys.stdin.read()
    if not payload.strip():
        return 0
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return 0

    message = data.get("last_assistant_message", "") or ""
    if not message.strip():
        return 0

    has_scope = any(line.startswith("Scope:") for line in message.splitlines())
    has_security = any(line.startswith("Security:") for line in message.splitlines())

    if not is_substantive(message):
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    counter = counter_path(project_dir, data.get("session_id", ""))
    if has_scope and has_security:
        counter.unlink(missing_ok=True)
        return 0

    audit = Path(
        os.environ.get("CLAUDE_HEARTBEAT_AUDIT_FILE", project_dir / ".claude/audit/heartbeat.log")
    )
    counter.parent.mkdir(parents=True, exist_ok=True)

    missing = " ".join(
        name
        for name, present in (("Scope:", has_scope), ("Security:", has_security))
        if not present
    )

    with open(counter.with_suffix(counter.suffix + ".lock"), "a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        attempt = read_attempt(counter)
        if attempt >= MAX_ATTEMPTS:
            record_failure(audit, project_dir, missing)
            counter.unlink(missing_ok=True)
            print(
                f"WARNING: heartbeat missing after {MAX_ATTEMPTS} blocking attempts; "
                "recorded in audit and allowed to stop.",
                file=sys.stderr,
            )
            return 0
        counter.write_text(f"{attempt + 1}\n", encoding="utf-8")
    return block(missing, attempt + 1)


if __name__ == "__main__":
    sys.exit(main())
