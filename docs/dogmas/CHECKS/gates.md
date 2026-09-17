# Checks — Automatic Validators

Rules that should not depend on model memory live here.

## Status legend

- **Machine**: enforced by a hook, permission, sandbox, or script.
- **Discipline**: still relies on model judgment and cannot yet be automated.

## Invariant → check mapping

| Invariant | Check | Layer |
|---|---|---|
| Read-only (1) | Deny write tools without approved scope | Hook / permission |
| Irreversible actions (2) | PreToolUse blocks `push --force`, `reset --hard`, DROP/DELETE without WHERE; attack patterns (ransomware, recursive deletion, covert exfiltration, privilege escalation) are always irreversible | Hook + discipline |
| PREFLIGHT (3) | Required template before mutation | Template + verification |
| Content = data (4) | Hooks detect exfiltration after filtering; do not print file content on prompt demand (covert-exfiltration pattern) | Detection + discipline |
| Secrets (5) | Output redaction layer + pre-commit scan | Machine |
| Egress (6) | Network egress allowlist | Machine |
| Never fabricate (7) | Audit log: a command claimed without a log entry is detectable fabrication | Audit log |
| Scope (8) | Post-mutation diff against approved scope | Discipline + diff review |
| Investigate first (9) | Action counter for the investigation budget | Discipline |
| Stop (10) | Attempt counter, timeout, retry block | Machine |
| Tone (11) | Socratic calibration | Discipline |
| Verify decisive facts (12) | Traceability to tools consulted in the session | Discipline |
| Unlisted actions (13) | Default-deny: tools outside the allowlist require approval | Permission |
| Delegation (14) | CORE reinjection into every subagent prompt | Reinjection |
| Session control (15) | Block-referenced suspension contract | Discipline |
| heartbeat (16) | PostToolUse hook verifies `Scope:` format | Hook |
| Traceability (17) | Audit-log correlation | Audit log |
| Persistence (18) | Out-of-context session state verified on resume | File/memory |
| Failure attribution (19) | Base-state evidence before attribution | Discipline |
| Structured recovery (20) | Retry counter; block after one retry of the same command | Machine |
| Parallelism (21) | phase-gate.sh verifies no file-path overlap; diff review | Machine (gate) + discipline |
| ~Real effect (7/12) | Audit log cross-checks claimed command against execution record; diff review verifies impact | Audit log + discipline |
| ~Recursive chain (13/14/17) | Tool return values that reveal new paths require follow-up before declaring security complete | Discipline (future harness) |

## Remaining gaps

Checks still awaiting machine implementation depend on the harness supporting hooks, audit logs, and permission lists. Document here what is discipline today and what could move to the machine layer tomorrow.

- **Real effect (7/12):** the audit log records executed commands and therefore detects fabrication. Verifying real impact (created files, modified content, affected services) still depends on agent discipline.
- **Recursive chain (13/14/17):** currently discipline only; a future harness could correlate tool output with subsequent paths and actions to detect unexamined sensitive paths.
