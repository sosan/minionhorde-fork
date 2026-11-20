# Phase Gate — Explicit File Integrity Checkpoint

Purpose: verify that required documents exist before an explicitly requested
phase transition, without depending on model memory or fuzzy intent detection.

## Explicit contract (C4 / POLA)

File: `.claude/hooks/phase-gate.sh`

The gate has exactly two invocation modes:

1. **CLI:** `.claude/hooks/phase-gate.sh <phase>`
2. **UserPromptSubmit marker:** a line that starts with `/gate <phase>`.

The marker must start a line. Prose that merely mentions `/gate` — for
example while discussing this hook — never triggers the gate. Natural-language
mentions such as `avanzar a fase 2`, `next phase`, or `continuar con la
planificación` never trigger the gate. Without an explicit marker or CLI
argument the script exits 0 silently.

Unknown explicit phases fail loudly with exit 2 and list the valid phases.

## Output and exit contract

- `PHASE_GATE_PASS: <phase>` on stdout, exit 0.
- `PHASE_GATE_FAIL: <reason>` on stderr, exit 2.
- No explicit trigger: no output, exit 0.

The CLI and marker modes call the same phase checks and must produce equivalent
results.

### Checks by phase

| Phase | Entry gate |
|------|------------|
| tier0/direct | None |
| tier1_phase1 | Verify that the `docs/` context directory exists |
| tier1_phase2 | Verify that `docs/PRD.md` and at least one spec exist |
| tier1_phase3 | Verify PRD + specs + test stubs |
| tier2_phase1 | Verify the `docs/` directory, `docs/PRD.md`, and at least one spec (impact analysis input) |
| tier2_phase2 | Verify the `docs/` directory, at least one spec, and test stubs (TDD before implementation) |
| tier3_phase1 | Verify the `docs/` directory exists (root-cause investigation) |
| tier3_phase2 | Verify the `docs/` directory and at least one test stub (regression test) |
| parallelism | Full-path overlap check over the roadmap (`docs/IMPLEMENTATION_ROADMAP.md` by default, override with `CLAUDE_PARALLEL_PLAN`); missing `Files:` declarations fail closed (CORE Inv 21) |

When `CLAUDE_TEST_CMD` is set, `tier1_phase3` and `tier3_phase2` also require
that command to fail. That proves the tests are red before implementation. The
check is opt-in because it runs the project's test suite.

### Registration in settings.json

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/phase-gate.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## What the gate does not do

- Does not create files or mutate the repository.
- Does not verify document quality, only declared prerequisites.
- Does not run the test suite unless `CLAUDE_TEST_CMD` is explicitly set.

## Manual and automated verification

The CLI is the primary manual path, not a fallback:

```bash
.claude/hooks/phase-gate.sh tier1_phase1
```

Focused tests are in `.claude/hooks/test_phase_gate.py` and cover CLI mode,
marker mode, CLI/marker parity, unknown phases, natural-language non-triggers,
and empty prompts.
