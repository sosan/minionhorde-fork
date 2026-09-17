#!/usr/bin/env bash
set -euo pipefail

# File Integrity Checkpoint gate — automatic execution via UserPromptSubmit.
# Reads the user prompt from stdin (JSON), detects an intent to advance a phase,
# and verifies prerequisites. If the gate fails, it blocks the prompt.

project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# --- Lectura del prompt ---
input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt // ""' 2>/dev/null || echo "")

# If there is no prompt, exit silently
[ -z "$prompt" ] && exit 0

# --- Detección de transición de fase ---
# We look for patterns indicating that the user wants to advance a phase
phase=""
if echo "$prompt" | grep -qiE 'avanzar a fase|continuar con|siguiente fase|fase [0-9]|de la fase|avanza al|pasa a la|next phase|advance to'; then
  if echo "$prompt" | grep -qiE 'tier1.*(phase[ 1]|fase[ 1]).*spec|spec.*tier1.*(phase[ 1]|fase[ 1])|PRD.*especif|especif.*PRD|tests.*spec|spec.*tests'; then
    phase="tier1_phase1"
  elif echo "$prompt" | grep -qiE 'tier1.*(phase[ 2]|fase[ 2]).*plan|plan.*tier1|(phase[ 2]|fase[ 2]).*planif|planif.*(phase[ 2]|fase[ 2])|implementación.*roadmap|roadmap.*implement'; then
    phase="tier1_phase2"
  elif echo "$prompt" | grep -qiE 'tier1.*(phase[ 3]|fase[ 3]).*im|im.*tier1|(phase[ 3]|fase[ 3]).*im|im.*desarroll|develop.*tier1'; then
    phase="tier1_phase3"
  elif echo "$prompt" | grep -qiE 'tier0|direct|rápido|sin pipeline'; then
    phase="tier0"
  fi
fi

# Si no se detectó fase, salir silenciosamente (no es una transición de fase)
[ -z "$phase" ] && exit 0

# --- Ejecución del gate ---
case "$phase" in
  tier1_phase1)
    # Antes de empezar Fase 1 (spec creation): verificar que no exista un PRD previo
    if [ -f "$project_dir/docs/PRD.md" ] && [ -s "$project_dir/docs/PRD.md" ]; then
      # PRD ya existe — posiblemente se está re-ejecutando. No bloquear.
      exit 0
    fi
    # Gate de salida de Fase 0: verificar que existe al menos un archivo de contexto
    # El hook no crea artefactos: solo verifica y bloquea si falta un requisito.
    # La primera fase no necesita un documento previo para comenzar.
    exit 0
    ;;
  tier1_phase2)
    # Antes de Fase 2 (planificación): verificar que PRD exista
    if [ ! -f "$project_dir/docs/PRD.md" ] || [ ! -s "$project_dir/docs/PRD.md" ]; then
      echo "PHASE_GATE_FAIL: docs/PRD.md no existe o está vacío. Completar Fase 1 antes de pasar a Fase 2." >&2
      exit 2
    fi
    # Verificar que exista al menos un spec
    if ! ls "$project_dir"/docs/specs/*.md >/dev/null 2>&1 || [ -z "$(ls "$project_dir"/docs/specs/*.md 2>/dev/null)" ]; then
      echo "PHASE_GATE_FAIL: No hay specs en docs/specs/. Crear al menos un spec antes de planificar." >&2
      exit 2
    fi
    exit 0
    ;;
  tier1_phase3)
    # Antes de Fase 3 (implementación): verificar PRD + specs + tests stubs
    for f in docs/PRD.md; do
      [ -f "$project_dir/$f" ] && [ -s "$project_dir/$f" ] || { echo "PHASE_GATE_FAIL: $f no existe o está vacío." >&2; exit 2; }
    done
    # Verificar specs
    if ! ls "$project_dir"/docs/specs/*.md >/dev/null 2>&1 || [ -z "$(ls "$project_dir"/docs/specs/*.md 2>/dev/null)" ]; then
      echo "PHASE_GATE_FAIL: No hay specs en docs/specs/." >&2
      exit 2
    fi
    # Verificar tests stubs
    found=0
    for p in "$project_dir"/tests/*.py "$project_dir"/tests/*.js "$project_dir"/tests/*.ts "$project_dir"/tests/*.go; do
      if [ -s "$p" ]; then found=1; break; fi
    done
    [ "$found" -eq 1 ] || { echo "PHASE_GATE_FAIL: No hay tests stubs en tests/." >&2; exit 2; }
    exit 0
    ;;
  tier0|direct)
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
