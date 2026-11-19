# Rule-drift checker

Purpose: keep derived instruction fragments synchronized with their canonical
source without depending on model memory.

File: `.claude/hooks/rule_drift.py`
Tests: `.claude/hooks/test_rule_drift.py` (run with
`python3 -m pytest .claude/hooks/test_rule_drift.py`)

## Marker format

Marked fragments use HTML comment lines in Markdown files:

```markdown
<!-- @rule:<name> @source:<canonical-path> @fragment:<id> -->
shared normative content
<!-- /@rule:<name> -->
```

- The canonical block lives in the file named by `@source` and repeats the same
  `@rule` with `@source` pointing to itself.
- Every other block with the same `@rule` must canonicalize to the same content
  as the canonical block.
- Canonicalization strips whitespace variance: it splits every line on
  whitespace, drops empty lines, and joins with single spaces, so re-indentation
  or re-wrapping does not produce drift.

## Current fragments

| Rule | Canonical source | Derived copies |
|---|---|---|
| `heartbeat` | `.claude/rules/DOGMAS-CORE.md` (Inv 16, `@fragment:inv16-format`) | `CLAUDE.md` Heartbeat section |

## Exit contract

- `0` — all marked fragments are consistent (or there is nothing marked yet).
- `1` — at least one `DRIFT_FAIL`, `ORPHAN_FAIL` (block without `@source`) or
  `SOURCE_MISSING` (`@source` file absent or lacking the rule).
- `2` — usage error.

Output messages are prefixed with the failure class, the file and line, and the
rule name, e.g.
`DRIFT_FAIL CLAUDE.md:122 rule 'heartbeat' diverges from canonical .claude/rules/DOGMAS-CORE.md:256`.

## Modes

- `--all` — check the default instruction files (`CLAUDE.md`, `AGENTS.md`,
  `.claude/rules/*.md`).
- `--changed` — check only Markdown files changed versus `HEAD` (for focused
  pre-commit use).
- Explicit file arguments — check the given files only.

## Registration

The checker is registered at the narrowest safe validation point: it runs as
part of the hook/security verification suite (`test_rule_drift.py`) and may be
invoked manually or from CI. It is intentionally not wired into
`PreToolUse`/`Stop` hooks to avoid adding latency to every session tool call.
