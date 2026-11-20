# Audit Log — JSON lines with a hash chain

Purpose: record security events without depending on an external service and
without letting a crafted command forge or corrupt entries.

## What to record

```
- timestamp (ISO 8601, UTC)
- event: tool_executed | irreversible_command | file_modified | secret_redacted
- tool: Bash | Write | Edit | Read | ...
- target: file or command, always redacted
- status: success | error | interrupted | warning
- redacted_types: labels of the patterns that fired
- prev_hash / hash: tamper-evident chain
```

## Storage

`.claude/audit/audit.log` — one JSON object per line (JSON Lines). Each entry
carries `prev_hash` (the previous entry's `hash`) and its own SHA-256 `hash`,
computed over the canonical JSON without the `hash` field.

Why JSON Lines:

- A command containing newlines stays inside one JSON string; it cannot inject
  fake YAML entries.
- The raw command is never written: `target` passes through the shared redactor
  first.
- The status comes from the hook event (`PostToolUseFailure` → `error`, or
  `tool_response.exit_code`/`is_error`).

Rotation: when the file reaches 1 MB it moves to `audit.log.1`, keeping three
rotated files.

## Registration

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash|Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/audit-log.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUseFailure": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/audit-log.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

`audit-log.sh` is a thin wrapper around `audit_log.py`; the Python module holds
the implementation and the shared redaction.

## Verify the chain

```bash
.claude/hooks/audit-log.sh --verify .claude/audit/audit.log
```

Prints `AUDIT_CHAIN_OK` (exit 0) or `AUDIT_CHAIN_FAIL` plus the broken lines
(exit 1). Verification detects edited entries and broken links. It cannot
detect truncation of the tail, because the tail has no successor to compare.

## Limits

- The log is local evidence, not a remote append-only store.
- A compromised process with write access can rewrite the whole chain.
- The redactor is pattern-based; it reduces exposure, it does not guarantee
  that no secret is ever written.
