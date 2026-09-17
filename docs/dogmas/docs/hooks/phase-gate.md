# Phase Gate — Automatic File Integrity Checkpoint

Purpose: verify that required documents exist before advancing a phase, without depending on model memory.

## Design

Each workflow phase has documentation prerequisites. The gate verifies that they exist before allowing the transition. If a prerequisite is missing, the hook returns `exit 2` (blocked) and the prompt is not processed.

## Current implementation

File: `.claude/hooks/phase-gate.sh`

The script:
1. Reads the user prompt from stdin (JSON format, via UserPromptSubmit hook).
2. Detects whether the prompt indicates an intent to advance a phase (the Spanish trigger phrases `"avanzar a fase"`, `"continuar con"`, `"siguiente fase"`, and `"fase 1/2/3"` are preserved because the hook matches them).
3. Identifies the target phase.
4. Runs the corresponding checks.
5. If it fails: `exit 2` (blocks the prompt).
6. If it passes: `exit 0` (the prompt is processed normally).

### Checks by phase

| Phase | Entry gate | Exit gate |
|------|----------------|----------------|
| tier0/direct | None | None |
| tier1_phase1 | Verify that no duplicate prior PRD exists | — |
| tier1_phase2 | Verify that `docs/PRD.md` and at least one spec exist | — |
| tier1_phase3 | Verify PRD + specs + test stubs | — |

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

### Behavior

- If the prompt does NOT indicate an intent to advance a phase → `exit 0` (does not interfere).
- If the prompt indicates an intent but a prerequisite is missing → `exit 2` (blocks the prompt and shows an error message to the operator).
- If the prompt indicates an intent and the gate passes → `exit 0` (the prompt is processed normally).

### What the gate does NOT do

- Does not create files. Does not mutate the repository.
- It is not exhaustive (it does not verify document quality, only existence).
- Does not cover all workflow phases (tier2, tier3, advanced phases).
- Depends on recognizing text patterns in the prompt (false negatives may occur if the operator uses undetected wording).

## Alternative: manual execution

If the hook does not work (classifier unavailable, prompt not detected), the PM can run:

```bash
.claude/hooks/phase-gate.sh tier1_phase1
```

The result is `PHASE_GATE_PASS` or `PHASE_GATE_FAIL: <reason>`.
