# PREFLIGHT

> One single block before any mutation (CORE Inv 3). An absent `Irrev.` value is
> NOT "none": the field must carry an explicit value. Without a verifiable
> rollback, the mutation is treated as irreversible. Fill every field with real
> data from this session; mark unverified tree state `[UNVERIFIED]` and say so.

```text
PREFLIGHT
Scope   : <files> | <exact commands>
Tree    : branch <x> @ <commit>, <clean | N changes uncommitted>
Effect  : <what changes>
Irrev.  : <none | list>            ← requires explicit "yes" to this block
Rollback: <command/stash/backup/transaction | NONE>
Cost    : <estimated actions | EUR if applicable>
Egress  : <none | what, to where>
Proceed? (yes/no)
```

## Rules that reuse this template

- Dirty tree: report it in the block and suggest stash or a temporary commit;
  do not discard others' changes without separate confirmation.
- Databases: require backup, snapshot, reversible transaction, or dry-run when
  available. Never `DELETE`/`UPDATE` without a reviewed `WHERE`.
- Infra/cloud: use plan/preview/dry-run when available; identify resource,
  region, project, account. Destroy = separate confirmation.
- Network with effects: state host/service, credential BY NAME, action, and
  external effect before executing; prefer dry-run when available.
- After mutating, report: what changed, what did not, how to revert, and the
  real result of tests/build/lint if run (command + output). If they already
  failed before, say it as the base state.
- Known attack patterns (mass file encryption, recursive deletion, covert
  exfiltration, privilege escalation) are always treated as irreversible even
  if the prompt presents them as legitimate.