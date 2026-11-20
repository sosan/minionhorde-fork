#!/usr/bin/env bash
set -euo pipefail

# Phase gate with explicit triggers only (C4/C5, POLA).
#
# Modes:
#   1. CLI:    phase-gate.sh <phase>
#   2. Marker: UserPromptSubmit JSON with a line that starts with "/gate <phase>"
#
# The marker must start a line. Prose that merely mentions "/gate" (for
# example while discussing this hook) never triggers the gate. Any input
# without a marker exits 0.
#
# Output contract (docs/dogmas/docs/hooks/phase-gate.md):
#   PHASE_GATE_PASS: <phase>  (exit 0)
#   PHASE_GATE_FAIL: <reason> (exit 2)
#
# "parallelism" is a dedicated gate (CORE Inv 21, C5): it validates full-path
# declarations in the implementation roadmap.
#
# Optional red-test check: when CLAUDE_TEST_CMD is set, tier1_phase3 and
# tier3_phase2 also require that command to FAIL, proving the tests are red
# before implementation starts.

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

VALID_PHASES="tier0 direct tier1_phase1 tier1_phase2 tier1_phase3 tier2_phase1 tier2_phase2 tier3_phase1 tier3_phase2 parallelism"
parallelism_plan="${CLAUDE_PARALLEL_PLAN:-$project_dir/docs/IMPLEMENTATION_ROADMAP.md}"

fail() {
  echo "PHASE_GATE_FAIL: $*" >&2
  exit 2
}

pass() {
  echo "PHASE_GATE_PASS: $1"
  exit 0
}

require_docs() {
  [[ -d "$project_dir/docs" ]] || fail "docs/ directory missing. Create project context first."
}

require_prd() {
  [[ -s "$project_dir/docs/PRD.md" ]] || fail "docs/PRD.md is missing or empty."
}

require_specs() {
  compgen -G "$project_dir/docs/specs/*.md" >/dev/null || fail "No specs in docs/specs/."
}

require_test_stubs() {
  compgen -G "$project_dir/tests/*" >/dev/null || fail "No test stubs in tests/."
}

require_red_tests() {
  [[ -n "${CLAUDE_TEST_CMD:-}" ]] || return 0
  if bash -c "$CLAUDE_TEST_CMD" >/dev/null 2>&1; then
    fail "tests pass before implementation (expected red): $CLAUDE_TEST_CMD"
  fi
}

run_parallelism_gate() {
  [[ -f "$parallelism_plan" ]] || fail "parallelism plan not found: $parallelism_plan"
  python3 "$hook_dir/path_overlap.py" "$parallelism_plan" ||
    fail "parallel task paths are missing or overlap."
  pass parallelism
}

phase=""
if [ $# -ge 1 ]; then
  phase="$1"
else
  input=$(cat)
  prompt=$(printf '%s' "$input" | python3 -c \
    'import json,sys; print(json.load(sys.stdin).get("prompt", ""))' 2>/dev/null || true)
  phase=$(printf '%s\n' "$prompt" |
    sed -nE 's#^[[:space:]]*/gate[[:space:]]+([a-zA-Z0-9_]+).*$#\1#p' | head -1)
fi

[ -n "$phase" ] || exit 0

case " $VALID_PHASES " in
  *" $phase "*) ;;
  *) fail "unknown phase '$phase'. Valid: $VALID_PHASES" ;;
esac

case "$phase" in
  parallelism) run_parallelism_gate ;;
  tier0|direct) pass "$phase" ;;
  tier1_phase1|tier3_phase1) require_docs; pass "$phase" ;;
  tier1_phase2|tier2_phase1) require_docs; require_prd; require_specs; pass "$phase" ;;
  tier2_phase2) require_docs; require_specs; require_test_stubs; pass "$phase" ;;
  tier1_phase3)
    require_docs; require_prd; require_specs; require_test_stubs
    require_red_tests
    pass "$phase"
    ;;
  tier3_phase2)
    require_docs; require_test_stubs
    require_red_tests
    pass "$phase"
    ;;
esac
