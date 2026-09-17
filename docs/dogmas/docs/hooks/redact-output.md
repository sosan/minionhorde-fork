# Output Redaction Layer — `redact-output.py`

> **Purpose:** redact secrets in tool output BEFORE they reach the model (policy B.6).
> **Type:** hook PostToolUse for Bash, with updatedToolOutput + additionalContext.
> **Infrastructure:** Python 3 + `jq` (already available on the system).

## What it does

1. Reads JSON from stdin (hook PostToolUse).
2. Extracts `tool_response.stdout` from the executed command.
3. Applies the patterns regex from policy Appendix A + entropy heuristic (≥32 chars alphanumeric characters in a secret-like variable name).
4. If matches are found:
   - Replaces the redacted stdout with `updatedToolOutput` (the model sees `[REDACTED:<type>]`).
   - Records in the audit log (types only, no secrets).
   - Adds `additionalContext` explaining what was redacted.
5. If there are no matches: `exit 0` with no output (does not interfere).

## Covered patterns (Appendix A)

- Cloud: AKIA/ASIA, aws_secret, AIza, private_key
- Git: ghp_, gho_, github_pat_, glpat-, glrt-
- AI/SaaS: sk-, hf_, r8_, gsk_, dop_v1_, dp.st., shpat_, NRAK-, PMAK-, secret_/ntn_
- Payments: sk_live_, rk_live_, whsec_, SG., slack webhook, discord webhook, telegram
- Infra: dckr_pat_, npm_, pypi-, hvs., AGE-SECRET-KEY
- Key material: PRIVATE KEY blocks (DOTALL)
- JWT: eyJ...eyJ...eyJ (three segments)
- Connection strings: postgresql://user:pass@, mysql://user:pass@
- Passwords: password=, pwd=, passwd=

Plus entropy heuristic: variable with a secret-like name + value ≥32 chars.

## Configuration

In `.claude/settings.json`:

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
      }
    ]
  }
}
```

## Output

The hook returns:
- `updatedToolOutput.stdout`: redacted output (when matches were found).
- `additionalContext`: "Secrets were redacted from Bash output (types: ...). The command already ran; only the output was hidden."
- Audit log in `.claude/audit/audit.log` with timestamp, tool, target, and detected types.

## Limitations

- Processes Bash stdout only (not Write/Edit files — those already go through the other hook's formatter).
- Cannot redact files written to disk — only command output.
- The patterns are from Appendix A (starter set) — they do not cover every possible format.
- For output exceeding 10k characters, Claude Code truncates it before it reaches the hook.
