#!/usr/bin/env bash
#
# minionhorde — Claude Code installer
#
# Installs the multi-agent SDLC harness into a project without destroying
# existing configuration:
#   * backs up the target's .claude/ and CLAUDE.md
#   * merges settings.json instead of overwriting it
#   * copies only runtime hooks (no tests, no __pycache__)
#   * copies the dogmas documentation without the eval harness
#   * never copies settings.local.json
#
# Usage:
#   ./install-claude.sh /path/to/project
#   ./install-claude.sh .                    # current directory
#
# Example:
#   ./install-claude.sh /tmp/demo && ls /tmp/demo/.claude/hooks
#   audit-log.sh  guard_pretooluse.py  phase-gate.sh  ...

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-.}"
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP_DIR="${HOME}/.claude_backups"

# Skills owned by the project (tracked in git). The user's local skills
# (jev-*, openspec-*, etc.) stay in their checkout and are never installed.
PROJECT_SKILLS="evaluation-contracts sdlc-workflow"

# ─── Validation ──────────────────────────────────────────────────────────────
[[ -d "$TARGET" ]] || { echo "Error: $TARGET is not a directory"; exit 1; }
[[ -d "$SCRIPT_DIR/.claude/agents" ]] || {
    echo "Error: source .claude/ not found. Run from the minionhorde repo root."
    exit 1
}
command -v python3 >/dev/null || { echo "Error: python3 is required"; exit 1; }

# ─── Backup ──────────────────────────────────────────────────────────────────
backup_existing() {
    local files=()
    [[ -e "$TARGET/.claude" ]] && files+=(".claude")
    [[ -e "$TARGET/CLAUDE.md" ]] && files+=("CLAUDE.md")

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "[i] No existing Claude config found — skipping backup"
        return
    fi

    mkdir -p "$BACKUP_DIR"
    local archive="$BACKUP_DIR/claude_conf_${TIMESTAMP}.tar.gz"
    echo "[...] Backing up ${files[*]} to $archive"
    if tar -czf "$archive" -C "$TARGET" "${files[@]}"; then
        echo "[OK] Backup created: $archive ($(du -h "$archive" | cut -f1))"
        echo "     Restore with: tar -xzf $archive -C $TARGET"
    else
        echo "[!] Backup failed — aborting so nothing is lost" >&2
        exit 1
    fi
}

# ─── Install ──────────────────────────────────────────────────────────────────
install_files() {
    mkdir -p "$TARGET/.claude/agents" "$TARGET/.claude/hooks" \
             "$TARGET/.claude/rules" "$TARGET/.claude/skills" \
             "$TARGET/docs" "$TARGET/docs/dogmas"

    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
    cp "$SCRIPT_DIR/.claude/agents/"*.md "$TARGET/.claude/agents/"
    cp "$SCRIPT_DIR/.claude/rules/"*.md "$TARGET/.claude/rules/"

    find "$SCRIPT_DIR/.claude/hooks" -maxdepth 1 -type f \
        \( -name '*.py' -o -name '*.sh' \) ! -name 'test_*' \
        -exec cp {} "$TARGET/.claude/hooks/" \;

    # Only the project's own skills are installed. User-local skills
    # (jev-*, openspec-*, ...) must not leak into a fresh project.
    for skill_name in $PROJECT_SKILLS; do
        skill_dir="$SCRIPT_DIR/.claude/skills/$skill_name"
        [[ -d "$skill_dir" ]] || continue
        mkdir -p "$TARGET/.claude/skills/$skill_name"
        cp -R "$skill_dir/". "$TARGET/.claude/skills/$skill_name/"
    done

    # Context templates are the *-Claude.md variants, not the OpenCode ones.
    # Never overwrite a project's existing context file.
    for template in "$SCRIPT_DIR/templates/context-files/"*-Claude.md; do
        destination="$TARGET/docs/$(basename "$template")"
        if [[ -e "$destination" ]]; then
            echo "[i] Keeping existing docs/$(basename "$template")"
        else
            cp "$template" "$destination"
        fi
    done

    # Merge, never overwrite: the target may already register its own hooks.
    python3 "$SCRIPT_DIR/scripts/merge_settings.py" \
        "$SCRIPT_DIR/.claude/settings.json" "$TARGET/.claude/settings.json"

    # The eval harness is research data, not part of the installed workflow.
    tar -C "$SCRIPT_DIR/docs/dogmas" \
        --exclude='./eval' --exclude='__pycache__' --exclude='*.pyc' \
        -cf - . | tar -C "$TARGET/docs/dogmas" -xf -
}

# ─── Verify ───────────────────────────────────────────────────────────────────
verify_install() {
    local ok=true
    local expected=(
        CLAUDE.md
        .claude/settings.json
        .claude/agents/project-manager.md
        .claude/hooks/guard_pretooluse.py
        .claude/hooks/redact-output.py
        .claude/hooks/audit_log.py
        .claude/hooks/audit-log.sh
        .claude/hooks/phase-gate.sh
        .claude/hooks/scope-validator.sh
        .claude/rules/workflow.md
        .claude/rules/DOGMAS-CORE.md
        .claude/rules/DOGMAS-REF-seed.md
        .claude/skills/sdlc-workflow/SKILL.md
        .claude/skills/evaluation-contracts/SKILL.md
        docs/PROJECT_CONTEXT-Claude.md
        docs/SPEC-Claude.md
        docs/dogmas/DOGMAS.md
        docs/dogmas/CHECKS/gates.md
    )
    local f
    for f in "${expected[@]}"; do
        if [[ -f "$TARGET/$f" ]]; then
            echo "[OK] $f"
        else
            echo "[FAIL] $f missing"
            ok=false
        fi
    done

    if [[ -e "$TARGET/docs/dogmas/eval" ]]; then
        echo "[FAIL] docs/dogmas/eval should not be installed"
        ok=false
    fi
    if [[ -e "$TARGET/.claude/hooks/__pycache__" ]]; then
        echo "[FAIL] .claude/hooks/__pycache__ should not be installed"
        ok=false
    fi
    if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' \
        "$TARGET/.claude/settings.json"; then
        echo "[FAIL] .claude/settings.json is not valid JSON"
        ok=false
    fi

    if [[ "$ok" == true ]]; then
        echo ""
        echo "Installation complete. Open Claude Code in $TARGET to start."
    else
        echo ""
        echo "Installation completed with errors. Check the failures above." >&2
        exit 1
    fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────
echo "minionhorde — Claude Code installer"
echo "Target: $TARGET"
echo ""

backup_existing
echo ""
install_files
echo ""
verify_install
