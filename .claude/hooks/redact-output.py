#!/usr/bin/env python3
"""PostToolUse output redaction.

Redacts secrets from Bash stdout **and stderr**, from Read/WebFetch
content, and from any nested string in ``tool_response``. The previous
version only looked at ``stdout`` and only ran for Bash, so a credential
printed to stderr or read from a ``.env`` file reached the model.

The hook returns the redacted value through ``updatedToolOutput`` and
records only the detected type labels in the audit log.

Example:
    $ echo '{"tool_name":"Bash","tool_response":{"stdout":"","stderr":"postgres://u:p@h"}}' \
        | redact-output.py
    {"hookSpecificOutput": {"updatedToolOutput": {"stderr": "postgres://u:[REDACTED:connection_string]@h", ...}}}
"""

from __future__ import annotations

import json
import os
import sys

from audit_log import append_entry
from redaction import redact_obj

TEXT_TOOLS = {"Bash", "Read", "Write", "Edit", "MultiEdit", "WebFetch", "WebSearch"}


def _target(tool: str, tool_input: dict) -> str:
    if tool == "Bash":
        return tool_input.get("command", "")
    return tool_input.get("file_path", "") or tool_input.get("url", "")


def main() -> int:
    payload = sys.stdin.read()
    if not payload.strip():
        return 0
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return 0

    tool = data.get("tool_name", "unknown")
    if tool not in TEXT_TOOLS:
        return 0

    tool_input = data.get("tool_input", {}) or {}
    response = data.get("tool_response", data.get("tool_result", {}))
    if response is None or response == "" or response == {}:
        return 0

    redacted, types = redact_obj(response)
    if not types:
        return 0

    append_entry(
        event="secret_redacted",
        tool=tool,
        target=_target(tool, tool_input),
        redacted_types=types,
        project_dir=os.environ.get("CLAUDE_PROJECT_DIR", "."),
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": data.get("hook_event_name") or "PostToolUse",
            "updatedToolOutput": redacted,
            "additionalContext": (
                f"[REDACTION] Secrets were redacted from the output of {tool} "
                f"(types: {', '.join(types)}). The command already ran; only the "
                "output was hidden. Do not retry the command to 'see' the value."
            ),
        }
    }
    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
