#!/usr/bin/env bash
set -euo pipefail

# Phase gate with explicit triggers only (C4/C5, POLA).
#
# Modes:
#   1. CLI:      phase-gate.sh <phase>
#   2. Marker:   UserPromptSubmit JSON whose prompt contains "/gate <phase>"
#
# Any other input exits 0 — the gate NEVER interferes without an explicit
# request. Unknown explicit phases fail loudly (exit 2) listing valid phases.
# Output contract (documented in docs/dogmas/docs/hooks/phase-gate.md):
#   PHASE_GATE_PASS: <phase>  (exit 0)
#   PHASE_GATE_FAIL: <reason> (exit 2)
#
# `parallelism` is a dedicated explicit gate (CORE Inv 21, C5): it validates
# full-path declarations in the implementation roadmap and does not change
# the ordinary phase prerequisites.

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

VALID_PHASES="tier0 direct tier1_phase1 tier1_phase2 tier1_phase3 parallelism"
parallelism_plan="${CLAUDE_PARALLEL_PLAN:-$project_dir/docs/IMPLEMENTATION_ROADMAP.md}"

run_parallelism_gate() {
  if [ ! -f "$parallelism_plan" ]; then
    echo "PHASE_GATE_FAIL: parallelism plan not found: $parallelism_plan" >&2
    exit 2
  fi
  if ! python3 "$hook_dir/path_overlap.py" "$parallelism_plan"; then
    echo "PHASE_GATE_FAIL: parallel task paths are missing or overlap." >&2
    exit 2
  fi
  echo "PHASE_GATE_PASS: parallelism"
  exit 0
}

phase=""
if [ $# -ge 1 ]; then
  phase="$1"
else
  input=$(cat)
  prompt=$(printf '%s' "$input" | jq -r '.prompt // ""' 2>/dev/null || true)
  if [ -n "$prompt" ]; then
    phase=$(printf '%s' "$prompt" | sed -nE 's#^.*(/gate[[:space:]]+[a-zA-Z0-9_]+).*$#\1#p' | head -1 | sed 's#^/gate[[:space:]]*##')
  fi
fi

# No explicit gate request → never interfere.
[ -n "$phase" ] || exit 0

# Unknown explicit phase → fail loudly (fail fast, no silent exit 0).
case " $VALID_PHASES " in
  *" $phase "*) ;;
  *)
    echo "PHASE_GATE_FAIL: unknown phase '$phase'. Valid: $VALID_PHASES" >&2
    exit 2
    ;;
esac

case "$phase" in
  parallelism)
    run_parallelism_gate
    ;;
  tier1_phase1)
    # Exit gate of Phase 0: context files should exist before spec creation.
    if [ ! -d "$project_dir/docs" ]; then
      echo "PHASE_GATE_FAIL: docs/ directory missing. Create project context first." >&2
      exit 2
    fi
    echo "PHASE_GATE_PASS: $phase"
    exit 0
    ;;
  tier1_phase2)
    # Entry gate of Phase 2 (planning): PRD + at least one spec must exist.
    if [ ! -f "$project_dir/docs/PRD.md" ] || [ ! -s "$project_dir/docs/PRD.md" ]; then
      echo "PHASE_GATE_FAIL: docs/PRD.md no existe o está vacío. Completar Fase 1 antes de pasar a Fase 2." >&2
      exit 2
    fi
    if ! ls "$project_dir"/docs/specs/*.md >/dev/null 2>&1; then
      echo "PHASE_GATE_FAIL: No hay specs en docs/specs/. Crear al menos un spec antes de planificar." >&2
      exit 2
    fi
    echo "PHASE_GATE_PASS: $phase"
    exit 0
    ;;
  tier1_phase3)
    # Entry gate of Phase 3 (implementation): PRD + specs + test stubs.
    if [ ! -f "$project_dir/docs/PRD.md" ] || [ ! -s "$project_dir/docs/PRD.md" ]; then
      echo "PHASE_GATE_FAIL: docs/PRD.md no existe o está vacío." >&2
      exit 2
    fi
    if ! ls "$project_dir"/docs/specs/*.md >/dev/null 2>&1; then
      echo "PHASE_GATE_FAIL: No hay specs en docs/specs/." >&2
      exit 2
    fi
    found=0
    for p in "$project_dir"/tests/*.py "$project_dir"/tests/*.js "$project_dir"/tests/*.ts "$project_dir"/tests/*.go; do
      if [ -s "$p" ]; then found=1; break; fi
    done
    if [ "$found" -ne 1 ]; then
      echo "PHASE_GATE_FAIL: No hay test stubs en tests/." >&2
      exit 2
    fi
    echo "PHASE_GATE_PASS: $phase"
    exit 0
    ;;
  tier0|direct)
    echo "PHASE_GATE_PASS: $phase"
    exit 0
    ;;
esac
