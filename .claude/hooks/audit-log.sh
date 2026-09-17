#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
event="tool_executed"
tool=$(printf '%s' "$input" | jq -r '.tool_name // "unknown"')
target=""
status="success"

case "$tool" in
  Bash)
    cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
    target="$cmd"
    if echo "$cmd" | grep -qEi '(push --force|reset --hard|DROP TABLE|DELETE FROM|TRUNCATE|rm -rf|sudo)'; then
      event="irreversible_command"
    fi
    ;;
  Write|Edit)
    target=$(printf '%s' "$input" | jq -r '.tool_input.file_path // "unknown"')
    event="file_modified"
    ;;
esac

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "${CLAUDE_PROJECT_DIR:-.}/.claude/audit"
printf -- '- timestamp: %s\n  event: %s\n  tool: %s\n  target: %s\n  status: %s\n' \
  "$timestamp" "$event" "$tool" "$target" "$status" \
  >> "${CLAUDE_PROJECT_DIR:-.}/.claude/audit/audit.log"

exit 0
