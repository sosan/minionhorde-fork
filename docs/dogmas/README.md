# DOGMAS — Procedural dogma bootstrap system

> Artifacts published from the OpenSpec change `bootstrap-agent-dogmas`
> (archived as `openspec/changes/archive/2026-09-14-bootstrap-agent-dogmas/`).
> This is the project's operational copy; the archive keeps the full history
> (including `eval/results/`, excluded here because it is evidence of past execution).

## Operational core (in `.claude/rules/`)

| File | Content |
|---|---|
| `.claude/rules/DOGMAS-CORE.md` | CORE v4.1 operational core — 20+ invariants in 4 blocks. Referenced by `CLAUDE.md` §DOGMAS. |
| `.claude/rules/DOGMAS-REF-seed.md` | Operational manual R0-R11 (definitions, preflight, git hygiene, response format). |

## Reference artifacts (in `docs/dogmas/`)

| Path | Content |
|---|---|
| `DOGMAS.md` | 5 abstract dogmas (D-01 to D-05) with traceability to policy and CORE. |
| `new-rule-ids.md` | 17 proposed rule IDs (integrated into `docs/agent_security_policy.md`). |
| `CASES/` | Worked cases: canonical, frontier, conflict, pressure, recovery, coordination, emergent. |
| `CHECKS/` | Automated validators and gates (invariant → machine layer enforcement matrix). |
| `MEMORY/` | Crystallized memory: incidents, patterns, refinement flow, promotion criteria. |
| `exam/` | Tone exam (evaluation matrix + curriculum by role/tier). |
| `tono/` | Theory of operational tone. |
| `eval/` | Evaluation scripts and prompts (run_eval.py, metrics.py, validate.py, intersect.py, prompts). No `results/` (history in archive). |
| `specs/` | Spec (AC-1 to AC-18) + deep analyses of the security policy. |
| `docs/` | Hook documentation, tutoring protocol, cross-model dissent, human judgment zone. |

## Enforcement hooks (in `.claude/hooks/`)

| Script | Event | Purpose |
|---|---|---|
| `format-after-edit.sh` | PostToolUse (Write\|Edit) | Formats black/prettier/gofmt |
| `audit-log.sh` | PostToolUse (Write\|Edit\|Bash) | Records events in `.claude/audit/audit.log` |
| `scope-validator.sh` | Stop | Validates `Scope:` + `Security:` (Inv 16) |
| `redact-output.py` | PostToolUse (Bash) | Redacts secrets in output |
| `phase-gate.sh` | UserPromptSubmit | Verifies phase prerequisites |
| PreToolUse inline | PreToolUse (Bash) | Blocks irreversible commands (Inv 2) |

## Installation

`./install-claude.sh <target>` copies `.claude/rules/DOGMAS-*.md`, `.claude/hooks/*`
and `docs/dogmas/` to the target project, and verifies their presence.

## Bootstrap

1. Read `DOGMAS-CORE.md` (core) + `DOGMAS-REF-seed.md` (manual).
2. Walk through the `CASES/` relevant to the role.
3. Follow `exam/curriculo.md` (sequence by role/tier).
4. Real work with external checks (`CHECKS/`) and heartbeat (`Scope:` / `Security:`).
