#!/usr/bin/env bash
set -euo pipefail

# Stop-hook heartbeat gate. Reads the last assistant message from stdin JSON.
# Exit 0 means no gate is required or the response is complete. Exit 2 blocks
# an incomplete substantive response. After two blocks, the hook records the
# bounded failure and degrades to a warning to avoid an infinite loop.
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"
counter_file="${CLAUDE_HEARTBEAT_COUNTER_FILE:-$project_dir/.claude/audit/heartbeat-retry.counter}"
audit_file="${CLAUDE_HEARTBEAT_AUDIT_FILE:-$project_dir/.claude/audit/heartbeat.log}"

input=$(cat)
last_message=$(printf '%s' "$input" | jq -r '.last_assistant_message // ""' 2>/dev/null || true)
[ -n "$last_message" ] || exit 0

line_count=$(printf '%s\n' "$last_message" | grep -cve '^[[:space:]]*$' || true)
has_scope=$(printf '%s\n' "$last_message" | grep -c '^Scope:' || true)
has_security=$(printf '%s\n' "$last_message" | grep -c '^Security:' || true)

# Keep this classifier deliberately bounded, matching the approved C3 matrix:
# a response is substantive when it already carries half a heartbeat, uses
# decision/risk vocabulary, or is long AND reasoned. Lists and short acks stay
# outside the gate, so the gate never blocks a factual answer.
is_substantive=false
# 1. Already carries one side of the heartbeat → the other side must be present.
if [ "$has_scope" -gt 0 ] || [ "$has_security" -gt 0 ]; then
  is_substantive=true
fi
# 2. Decision/risk vocabulary.
if printf '%s' "$last_message" | grep -qiE '(decision|justification|applicable rule|alternative|preflight|impact|reversibility|recommend|diagnos|risk|propos|disagree|approved|rejected|recomiendo|propongo|riesgo|sugiero)'; then
  is_substantive=true
fi
# 3. Long AND reasoned (length alone never triggers the gate).
if [ "$line_count" -ge 8 ] && printf '%s' "$last_message" | grep -qiE '(because|therefore|porque|ya que|debido a|dado que|as a result)'; then
  is_substantive=true
fi

if [ "$is_substantive" = false ]; then
  rm -f "$counter_file"
  exit 0
fi

if [ "$has_scope" -gt 0 ] && [ "$has_security" -gt 0 ]; then
  rm -f "$counter_file"
  exit 0
fi

mkdir -p "$(dirname "$counter_file")"
lock_dir="${counter_file}.lock"
while ! mkdir "$lock_dir" 2>/dev/null; do sleep 0.01; done
trap 'rmdir "$lock_dir" 2>/dev/null || true' EXIT

attempt=$(cat "$counter_file" 2>/dev/null || echo 0)
case "$attempt" in
  ''|*[!0-9]*) attempt=0 ;;
esac

if [ "$attempt" -ge 2 ]; then
  mkdir -p "$(dirname "$audit_file")"
  printf '%s\n' "heartbeat_missing_after_retries" >> "$audit_file"
  rm -f "$counter_file"
  echo "WARNING: heartbeat missing after 2 blocking attempts; recorded in audit and allowed to stop." >&2
  exit 0
fi

attempt=$((attempt + 1))
tmp_counter="${counter_file}.tmp.$$"
printf '%s\n' "$attempt" > "$tmp_counter"
mv -f "$tmp_counter" "$counter_file"

missing=""
[ "$has_scope" -gt 0 ] || missing="Scope:"
[ "$has_security" -gt 0 ] || missing="${missing:+$missing }Security:"
printf '{"hookSpecificOutput":{"hookEventName":"Stop","decision":"block","reason":"CORE Inv 16: substantive response missing %s (attempt %s/2)"}}\n' "$missing" "$attempt"
echo "BLOCK: CORE Inv 16 requires $missing (attempt $attempt/2)." >&2
exit 2
