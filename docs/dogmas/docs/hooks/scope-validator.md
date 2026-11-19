# Scope Validator — Automatic security heartbeat

Purpose: verify that every substantive response ends with `Scope:` and the
security line, without depending on model memory.

## CORE rule (Inv 16)

> Every substantive response ends with `Scope: complete.` or
> `Scope: covered X; did not cover Y because Z; assumed W.` plus one
> `Security:` line:
> `[nothing to declare | mutated with order+preflight | irreversible: X |
> secrets: Y | egress: Z | fabrication: S]`

The canonical fragment lives in DOGMAS-CORE Inv 16 (`@rule:heartbeat`) and is
duplicated verbatim in `CLAUDE.md`; the rule-drift checker keeps them in sync.

## Implementation (fail-fast Stop gate, C3)

File: `.claude/hooks/scope-validator.sh` — registered as a `Stop` hook in
`settings.json`. Behavior:

- Non-substantive responses (short acks, factual lists, one-sided length) exit 0.
- A substantive response is one that already carries half a heartbeat, uses
  decision/risk vocabulary, or is ≥8 non-empty lines AND contains a reasoning
  connective. Length alone never triggers the gate.
- A substantive response missing `Scope:` or `Security:` is **blocked**:
  stdout carries
  `{"hookSpecificOutput":{"hookEventName":"Stop","decision":"block","reason":"..."}}`
  and the script exits 2. The message names the missing field and the attempt.
- Attempts persist in `.claude/audit/heartbeat-retry.counter` (atomic rename,
  guarded by a lock directory). A complete heartbeat resets the counter.
- After 2 blocked attempts, the hook records
  `heartbeat_missing_after_retries` in `.claude/audit/heartbeat.log`, clears the
  counter, and exits 0 with a stderr warning — the bounded escape valve that
  prevents an infinite Stop-hook loop.

Tests: `.claude/hooks/test_scope_validator.py` covers short acks, factual
lists, blocking, scope-without-security, complete heartbeat, the retry
sequence (2 blocks then warning), and empty input.

## Registration in settings.json

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
