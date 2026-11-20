# Output Redaction Layer — `redact-output.py`

> **Purpose:** redact secrets in tool output BEFORE they reach the model.
> **Type:** PostToolUse and PostToolUseFailure for Bash, Read, WebFetch, WebSearch.
> **Infrastructure:** Python 3 standard library only (no `jq`, no packages).

## What it does

1. Reads the hook JSON from stdin.
2. Redacts every string in `tool_response`, recursively — not just
   `tool_response.stdout`.
3. If something matched:
   - Returns `updatedToolOutput` with the same shape and `[REDACTED:<type>]`
     markers, so the model never sees the value.
   - Adds `additionalContext` explaining what was redacted.
   - Appends `secret_redacted` to the audit log with the type labels only.
4. If nothing matched: exits 0 with no output and does not interfere.

Coverage that the previous version missed:

| Surface | Before | Now |
|---------|--------|-----|
| Bash `stdout` | redacted | redacted |
| Bash `stderr` | leaked | redacted |
| Failed commands (`PostToolUseFailure`) | leaked | redacted |
| `Read` of a `.env` or key file | leaked | redacted |
| `WebFetch` / `WebSearch` content | leaked | redacted |
| JSON `{"password": "..."}` | leaked | redacted |
| Nested objects/lists | ignored | redacted recursively |

## Shared module

Patterns and recursive redaction live in `.claude/hooks/redaction.py`:

- `redact(text) -> (text, types)` for plain strings.
- `redact_obj(value) -> (value, types)` for hook payloads.

`audit_log.py` imports the same module, so the audit `target` and the model
output use identical patterns.

## Covered patterns

- Cloud: AKIA/ASIA/AIDA, aws_secret, AIza, GCP private key
- Git: ghp_/gho_/ghu_/ghs_/ghr_, github_pat_, glpat-, glrt-
- AI/SaaS: sk-, hf_, r8_, gsk_, dop_v1_, dp.st., shpat_, NRAK-, PMAK-,
  secret_/ntn_
- Payments/messaging: sk_live_, rk_live_, whsec_, SG., Slack/Discord webhooks,
  Telegram bot tokens
- Infra: dckr_pat_, npm_, pypi-, hvs., AGE-SECRET-KEY
- Key material: `BEGIN ... PRIVATE KEY` blocks
- JWT: `eyJ...` three-segment tokens
- Authorization headers: `Bearer`, `Basic`, `Token`, `ApiKey`
- Connection strings: postgres/mysql/mongodb/redis/amqp/ldap/smb/sftp/s3/gs
- URL secret parameters: `?token=`, `&key=`, `X-Amz-Signature=`
- JSON and `key=value` assignments: password, secret, token, api_key,
  client_secret, access_key, private_key, aws_secret_access_key
- Entropy heuristic: secret-like name + value ≥32 characters

## Configuration

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/redact-output.py\"",
            "timeout": 15
          }
        ]
      },
      {
        "matcher": "Read|WebFetch|WebSearch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/redact-output.py\"",
            "timeout": 15
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
            "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/redact-output.py\"",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

## Limits

- Pattern-based: it reduces exposure, it does not prove the absence of secrets.
- It cannot redact a file already written to disk; it only hides the output.
- `updatedToolOutput` must keep the tool's output shape. The hook echoes the
  original object with strings replaced, so the shape is preserved.
- Claude Code may truncate very large outputs before the hook sees them.
- If the tool is not in `TEXT_TOOLS`, the hook exits 0 untouched.
