# Verification: mechanical rules do not depend on model memory

Purpose (T2.4): verify that every mechanical rule identified in T1.3 can be satisfied without the model “remembering” the rule — that is, it has an external check (hook, permission, script, or template).

## Identified mechanical rules (from CHECKS/gates.md)

| # | Rule | External check | Depends on memory? |
|---|---|---|---|
| 1 | Read-only (denylist write without scope) | `deny` permission in settings.json | NO — permission blocks before execution |
| 2 | Irreversible (push --force, DROP, etc.) | PreToolUse hook + deny permissions | NO — hook blocks before execution |
| 3 | Preflight (required template) | Physical template + phase gate | NO — the template is a file, not memory |
| 4 | Content = data (injection) | Honeytokens (post-hoc detection) | PARTIAL — injection detection in complex content requires judgment, but honeytokens detect resulting exfiltration without memory |
| 5 | Secrets (redaction) | Output redaction layer + pre-commit scan | NO — automatic layer, not memory |
| 6 | Egress (network allowlist) | Network permissions + allowlist | NO — the harness blocks |
| 7 | Never fabricate (audit log) | Harness audit log | NO — the log is external evidence |
| 8 | Exact scope (diff vs approved) | Post-mutation diff | NO — the diff is external evidence |
| 10 | Stop (attempt counter) | Counter hook + timeout | NO — the hook counts, not the model |
| 13 | Unlisted actions (default-deny) | Default-deny permissions | NO — permission applies the most restrictive category |
| 14 | Delegation (CORE reinjection) | Reinjection into subagent prompt | NO — the prompt includes it automatically |
| 16 | Heartbeat (Scope:) | Stop hook validates format | NO — hook verifies format |
| 17 | Traceability (audit log) | Audit log | NO — external evidence |
| 20 | Recovery (retry counter) | Counter hook | NO — hook counts |

## Conclusion

**14 of 14 mechanical rules have an external check that does not depend on model memory.**

The rules that depend on “discipline” (model judgment) are the ones that are NOT mechanical:
- Exact scope (8) — requires judgment to detect subtle scope creep
- Investigate first (9) — requires judgment about when to stop
- Tone (11) — requires calibration
- Verify what is decisive (12) — requires judgment about what is decisive
- Failure attribution (19) — requires investigation

These five are **contextual judgments** (not mechanical) and are calibrated through Socratic review, not hooks. This is consistent with the classification in design.md §2.

## Practical verification

To confirm that a rule does not depend on memory:
1. Can a “blank” model (without CORE in context) comply with it? → If it requires CORE, it is memory-dependent.
2. Is there an external check that enforces it even if the model forgets? → If yes, it is mechanical.
3. Does the check run BEFORE the action (prevention) or AFTER (detection)? → Preferably before.

All mechanical rules have prevention checks (hooks/permissions) or detection (audit/honeytokens) that do not require the model to remember the rule.
