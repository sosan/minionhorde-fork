# Command Guard — `guard_pretooluse.py`

> **Purpose:** deny irreversible or security-weakening Bash commands before
> they run.
> **Type:** PreToolUse for `Bash`.
> **Infrastructure:** Python 3 standard library only (`shlex`, `json`).

## Why a hook and not only deny patterns

`permissions.deny` matches the literal command prefix. It misses
`rm -r -f` when the rule says `rm -rf`, and it cannot see inside
`bash -c '...'`, `xargs`, `env`, or `python -c`. The guard tokenizes the
command, strips wrappers and assignments, and checks each simple command
separately. That also removes false positives such as
`grep -r 'rm -rf' docs/`, where the dangerous text is an argument, not a
command.

## Contract

| Input | Output |
|-------|--------|
| JSON on stdin with `tool_name` and `tool_input.command` | exit 0 to allow |
| Same, when a rule matches | exit 2 + `permissionDecision: deny` JSON, reason repeated on stderr |

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Blocked by guard_pretooluse: <reason>. Use the explicit approval flow (CORE Inv 2)."
  }
}
```

A non-`Bash` tool, empty input, or invalid JSON exits 0: the guard is not the
place to fail closed on malformed harness payloads.

## What it blocks

| Area | Examples |
|------|----------|
| Privilege | `sudo ...` |
| Recursive delete | `rm -r`, `rm -f`, `rm -r -f`, `rm --recursive` |
| `find` deletion | `find . -delete`, `find . -exec rm {} +` |
| Git history/state | `push --force`, `push --force-with-lease`, `push --delete`, `push origin :branch`, `reset --hard`, `clean -f`, `checkout -- .`, `restore .`, `stash drop/clear`, `branch -D`, `tag -d`, `--no-verify` |
| Shell indirection | `bash -c '<dangerous>'`, `eval '<dangerous>'`, backticks outside single quotes |
| Remote code | `curl ... \| bash`, `wget ... \| sh`, `bash <(curl ...)` |
| Interpreters | `python -c` with `shutil.rmtree`, `os.remove`, `subprocess.`, `verify=False`; `ruby -e`; `node -e` |
| TLS weakening | `curl -k`, `--insecure`, `--no-check-certificate`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `PYTHONHTTPSVERIFY=0`, `verify=False` |
| Permissions | `chmod 777`, `chmod -R 777`, `umask 000` |
| Disk | `dd of=/dev/...`, `mkfs*`, `shred`, `wipefs`, `fdisk`, `parted` |
| SQL | `psql -c 'DROP TABLE ...'`, `DELETE FROM`, `TRUNCATE` |
| Exposure | `--privileged`, `0.0.0.0` |

Wrappers such as `command`, `builtin`, `exec`, `time`, `nohup`, `nice`,
`ionice`, `stdbuf`, `env`, and `xargs` are stripped before the check, so
`env rm -rf /` and `xargs rm -rf` are blocked too.

## Registration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/guard_pretooluse.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Tests

```bash
python3 -m pytest .claude/hooks/test_guard_pretooluse.py -q
```

The suite is a table of blocked and allowed commands plus the CLI contract
(deny JSON and exit 2, allow exit 0). Add a case to the table before adding a
rule.

## Limits

- It inspects the command string. `bash script.sh` is allowed; the contents of
  the script are not inspected.
- It is a guardrail, not a sandbox. A command it does not model can still be
  destructive; the operator approval flow remains the authority (CORE Inv 2).
- It can block legitimate work (`rm -f` on a build artifact). That is
  deliberate: ask the operator for an explicit, scoped approval instead of
  weakening the rule.
