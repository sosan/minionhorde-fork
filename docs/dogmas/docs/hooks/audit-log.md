# Audit Log — Compliance manual (minimum viable)

Purpose: record security events without depending on an external harness.

## What to record

Each relevant event is recorded in `audit-log.md` in the project (or in session memory) with:

```
- timestamp (ISO 8601)
- event: command_executed | file_modified | secret_detected | injection_detected | approval_given | rollback_used
- tool: Bash | Write | Edit | ...
- target: file or command (sin secretos)
- agent: who executed it
- phase: workflow phase
- status: success | blocked | error
```

## Events that trigger logging

- Irreversible command executed (even if it passed the filter)
- File modified outside the approved scope
- Secret detected in output
- Injection reported
- Operator approval for an irreversible action
- Rollback executed

## Minimal implementation (without a harness)

Until a harness audit log exists, the agent keeps a session-memory log and flushes it to the `Stop` for each turn. Formato:

```markdown
## audit_2026-09-09T02:00:00Z
- event: command_executed | tool: Bash | target: git status | status: success
- event: file_modified | tool: Edit | target: src/auth/handler.ts | status: success
```

## Hook implementation (when the classifier allows writing)

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash|Write|Edit",
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

The script `.claude/hooks/audit-log.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
event="tool_executed"
tool=$(printf '%s' "$input" | jq -r '.tool_name // "unknown"')
tool_input=$(printf '%s' "$input" | jq -c '.tool_input')
tool_response=$(printf '%s' "$input" | jq -c '.tool_response')
status="success"

# Detect event type
case "$tool" in
  Bash)
    cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
    if echo "$cmd" | grep -qEi '(push --force|reset --hard|DROP TABLE|DELETE FROM|TRUNCATE|rm -rf|sudo)'; then
      event="irreversible_command"
    fi
    target="$cmd"
    ;;
  Write|Edit)
    target=$(printf '%s' "$input" | jq -r '.tool_input.file_path // "unknown"')
    event="file_modified"
    ;;
esac

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write to the local audit log (sin secretos)
mkdir -p "${CLAUDE_PROJECT_DIR}/.claude/audit"
printf -- '- timestamp: %s\n  event: %s\n  tool: %s\n  target: %s\n  status: %s\n' \
  "$timestamp" "$event" "$tool" "$target" "$status" \
  >> "${CLAUDE_PROJECT_DIR}/.claude/audit/audit.log"

exit 0
```

Make executable: `chmod +x .claude/hooks/audit-log.sh`
