# Hook and security verification (task 8.4)

> Task 8.4 of `openspec/changes/develop-agent-layers`.
> Date: 2026-10-06 (branch `feature-bootstrapping`).
> Status: verification report — the new evaluation path (provider adapters,
> coverage gates, safe runner) is NOT enabled by default; this gate confirms
> existing hooks and security tests still pass before any future default.

## What this verifies

The evaluation change adds a new path (`contract.providers`,
`contract.safe_runner`, `contract.coverage_gates`, `contract.anonymizer`)
that reads secrets from env only and never persists them. Before enabling
that path **by default** (e.g. wiring it into CI or a default runner), the
existing machine controls and security tests must still pass. This report
is the evidence for that gate.

## 1. Hook configuration (Layer A machinery)

All five hooks are wired in `.claude/settings.json` and present on disk
(`.claude/hooks/`, `ls -la` verified, all executable):

| Hook | Trigger | Source |
|------|---------|--------|
| `audit-log.sh` | PostToolUse (Write/Edit/Bash) | `.claude/hooks/audit-log.sh` |
| `redact-output.py` | PostToolUse (Bash) | `.claude/hooks/redact-output.py` |
| format (black/prettier/gofmt) | PostToolUse (Write/Edit) | inline in `settings.json` |
| irreversible-command guard | PreToolUse (Bash) | inline in `settings.json` |
| `scope-validator.sh` | Stop | `.claude/hooks/scope-validator.sh` |
| `phase-gate.sh` | UserPromptSubmit | `.claude/hooks/phase-gate.sh` |

## 2. Hook behavior tests (executed in this session, 2026-10-06)

Tests ran with simulated harness JSON on stdin, writing only to
`/tmp/...` — no repo files mutated by the verification itself.

| # | Test | Input | Expected | Actual | Result |
|---|------|-------|----------|--------|--------|
| 1 | audit-log Write event | `{"tool_name":"Write","tool_input":{"file_path":"src/example.py"}}` | appends `file_modified` to audit log | appended, target `src/example.py` | PASS |
| 2 | audit-log irreversible detection | Bash input with `sudo rm -rf ... && psql -c "DROP TABLE users"` | appends `irreversible_command` | appended, event `irreversible_command` | PASS |
| 3 | PreToolUse irreversible guard | Bash `git push --force origin main` | outer guard denies with Inv 2 reason | denied: "Comando irreversible o que debilita seguridad (Inv 2 del CORE)" | PASS |
| 4 | scope-validator substantive w/o Scope | message with decision/justification, no `Scope:` | warnings for Scope + Security | both warnings emitted, exit 0 | PASS |
| 5 | scope-validator with Scope+Security | message ending `Scope: complete.` + `Security: nothing to declare.` | silent | silent, exit 0 | PASS |
| 6 | phase-gate tier1 phase2 missing PRD | prompt advancing to fase 2, no `docs/PRD.md` | `PHASE_GATE_FAIL`, exit 2 | `PHASE_GATE_FAIL: docs/PRD.md no existe o está vacío. Completar Fase 1 antes de pasar a Fase 2.`, exit 2 | PASS |
| 7 | phase-gate non-phase prompt | "just fixing a typo, not a phase advance" | silent | silent, exit 0 | PASS |
| 8 | redact-output GitHub token | Bash stdout containing `ghp_...` | redacted output + audit entry | `[REDACTED:secret_assignment]`, types `github_token, secret_assignment` | PASS |

Notes:
- Test 3 executed through the actual session PreToolUse hook; the model
  never saw the raw token in test 8 — the redaction hook intercepted it.
- The `format-after-edit.sh` hook (black/prettier/gofmt) is exercised
  implicitly every time a `Write`/`Edit` matches; no standalone test is
  needed because it degrades gracefully (`|| true`).

## 3. Security test suite (contract tests)

Command: `python3 -m pytest -q` in `docs/dogmas/eval/contract/`.

Result: **392 passed, 1 failed** (393 collected).

### The single failure is pre-existing and unrelated

```
FAILED test_trajectory_provenance.py::test_validate_against_schema_reports_invalid_record
    assert any("schema_version" in error for error in errors)
    assert False
```

- `git log` for `test_trajectory_provenance.py` shows the test was
  committed with the trajectory-provenance integration
  (`4273252`, `9dea331`) — before any of this session's work.
- `git diff HEAD -- docs/dogmas/eval/contract/` is **empty**: no contract
  code changed in this session. The failure is base state, not caused by
  the evaluation change (CORE Inv 19 — failure attribution).
- The same failure is already recorded in `BASELINE_SAFE_RUN.md` (§
  Limitations, "The 1 pre-existing failing test ... was failing before
  this change").

Security-relevant suites that specifically pass:

| Suite | Tests | Focus |
|-------|-------|-------|
| `test_layer_authority.py` | 8 | Layer C cannot disable controls, weaken redaction, bypass gates, authorize irreversible, or modify Layer B without human approval |
| `test_layer_profiles.py` | profile validation, hash integrity | serialized Layer A/B profiles |
| `test_safe_runner.py` | 9 | envelopes never persist responses; anonymized report has no prompts; coverage gates block global scope |
| `test_providers.py` | provider adapters, envelope hashing | secrets from env only, never persisted |
| `test_anonymizer.py` | report format, hash-only default | no prompt/response text in shareable artifacts |
| `test_memory_contamination.py` | contamination marking, transfer exclusion | contaminated cases excluded from transfer claims |
| `test_p2_7.py` | memory lifecycle | redaction before storage, conflicts, budgets, revalidation |

## 4. Conclusion

The existing hooks and security tests remain passing. The single failing
test is a pre-existing, unrelated base-state failure already documented in
the baseline report. No regression was introduced by the evaluation
change. **Gate passes**: the new path may be enabled by default in a
future step without weakening existing controls.

## 5. Limitations of this verification

- Hook tests use simulated JSON input, not a live Claude Code session
  end-to-end (the harness itself already runs the hooks on every
  Write/Edit/Bash in this session; the audit log under `.claude/audit/`
  is the byproduct).
- `redact-output.py` was tested against the GitHub-token pattern and the
  entropy heuristic; the full Appendix A pattern table is inherited from
  `docs/agent_security_policy.md` and is exercised in the security test
  suite via `contract/anonymizer`.
- Provider adapters (`anthropic`, `openai`) were not exercised against
  real credentials; their error paths are tested with fake SDKs
  (`test_providers.py`). No real provider call was made.
