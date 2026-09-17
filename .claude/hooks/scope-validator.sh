#!/usr/bin/env bash
set -euo pipefail

# Reads the last assistant message from stdin JSON.
input=$(cat)
last_message=$(printf '%s' "$input" | jq -r '.last_assistant_message // ""')

# If there is no message, do nothing.
[ -n "$last_message" ] || exit 0

# Detect whether this is a substantive response (more than 3 lines or contains indicators)
line_count=$(printf '%s' "$last_message" | wc -l)
has_scope=$(printf '%s' "$last_message" | grep -c '^Scope:' || true)
has_security=$(printf '%s' "$last_message" | grep -c '^Security:' || true)

is_substantive=false
if [ "$line_count" -gt 3 ]; then
  is_substantive=true
fi
if printf '%s' "$last_message" | grep -qiE '(decision|justification|applicable rule|alternative|preflight|impact|reversibility)'; then
  is_substantive=true
fi

if [ "$is_substantive" = true ]; then
  if [ "$has_scope" -eq 0 ]; then
    echo "WARNING: Substantive response without 'Scope:'. CORE rule Inv 16 requires a heartbeat in every substantive response." >&2
  fi
  if [ "$has_security" -eq 0 ]; then
    echo "WARNING: Substantive response without 'Security:'. CORE rule Inv 16 requires a security line." >&2
  fi
fi

exit 0
