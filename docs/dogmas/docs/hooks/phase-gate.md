# Phase Gate — Explicit File Integrity Checkpoint

Purpose: verify that required documents exist before an explicitly requested
phase transition, without depending on model memory or fuzzy intent detection.

## Explicit contract (C4 / POLA)

File: `.claude/hooks/phase-gate.sh`

The gate has exactly two invocation modes:

1. **CLI:** `.claude/hooks/phase-gate.sh <phase>`
2. **UserPromptSubmit marker:** include `/gate <phase>` in the prompt JSON.

Natural-language mentions such as `avanzar a fase 2`, `next phase`, or
`continuar con la planificación` never trigger the gate. Without an explicit
marker or CLI argument the script exits 0 silently.

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
| parallelism | Full-path overlap check over the roadmap (`docs/IMPLEMENTATION_ROADMAP.md` by default, override with `CLAUDE_PARALLEL_PLAN`); missing `Files:` declarations fail closed (CORE Inv 21) |

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
- Does not cover tier2, tier3, or advanced workflow phases yet; expanding
  coverage requires a separate acceptance criterion and failing case.

## Manual and automated verification

The CLI is the primary manual path, not a fallback:

```bash
.claude/hooks/phase-gate.sh tier1_phase1
```

Focused tests are in `.claude/hooks/test_phase_gate.py` and cover CLI mode,
marker mode, CLI/marker parity, unknown phases, natural-language non-triggers,
and empty prompts.
