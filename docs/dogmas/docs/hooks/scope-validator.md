# Scope Validator — Automatic security heartbeat

Purpose: verify that every substantive response ends with `Scope:` and the security line, without depending on model memory.

## CORE rule (Inv 16)

> Every substantive response ends with `Scope: completo.` or `Scope: cubrí X; no cubrí Y por Z; asumí W.`
> with security line: `Security: [nada que declarar | muté con orden+preflight | irreversible: X | secretos: Y | egreso: Z | fabricación: S]`

The Spanish text in these examples is a preserved protocol literal; the hook currently matches `Security:`.

## Implementation as a Stop hook (apply when the classifier allows it)

File: `.claude/hooks/scope-validator.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Reads the last assistant message from stdin JSON
input=$(cat)
last_message=$(printf '%s' "$input" | jq -r '.last_assistant_message // ""')

# If there is no message, do nothing
[ -n "$last_message" ] || exit 0

# Detect whether it is a substantive response (more than 3 lines or contains indicators)
line_count=$(printf '%s' "$last_message" | wc -l)
has_scope=$(printf '%s' "$last_message" | grep -c '^Scope:' || true)
has_security=$(printf '%s' "$last_message" | grep -c '^Security:' || true)

# Substantive response = more than 3 lines and not only a list/ack
is_substantive=false
if [ "$line_count" -gt 3 ]; then
  is_substantive=true
fi
# Contains a recommendation, analysis, decision, etc.
if printf '%s' "$last_message" | grep -qiE '(decision|justification|applicable rule|alternative|preflight|impact|reversibility)'; then
  is_substantive=true
fi

if [ "$is_substantive" = true ]; then
  if [ "$has_scope" -eq 0 ]; then
    echo "WARNING: Substantive response without 'Scope:'. CORE rule Inv 16 requires a heartbeat in every substantive response." >&2
    # Do not block (exit 0), only warn via stderr
  fi
  if [ "$has_security" -eq 0 ]; then
    echo "WARNING: Substantive response without 'Security:'. CORE rule Inv 16 requires a security line." >&2
  fi
fi

exit 0
```

## Integration with settings.json

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/scope-validator.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Alternative without hooks (discipline)

Until settings.json can be written, the agent manually includes the heartbeat at the end of every substantive response. This is already in the published CORE v4.1.
