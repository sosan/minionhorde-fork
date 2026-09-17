#!/usr/bin/env bash
#
# minionhorde — Claude Code Installation Script
# Backs up existing Claude config and installs the multi-agent SDLC harness
#
# Usage:
#   ./install-claude.sh /path/to/project
#   ./install-claude.sh .                    # current directory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-.}"
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP_DIR="${HOME}/.claude_backups"

# ─── Validation ──────────────────────────────────────────────────────────────
[[ -d "$TARGET" ]] || { echo "Error: $TARGET is not a directory"; exit 1; }
[[ -d "$SCRIPT_DIR/.claude/agents" ]] || { echo "Error: Source .claude/ not found. Run from minionhorde repo root."; exit 1; }

# ─── Backup ──────────────────────────────────────────────────────────────────
backup_existing() {
    local has_backup=false
    local files_to_backup=()

    if [[ -d "$TARGET/.claude" ]]; then
        files_to_backup+=("$TARGET/.claude")
        has_backup=true
    fi

    if [[ -f "$TARGET/CLAUDE.md" ]]; then
        files_to_backup+=("$TARGET/CLAUDE.md")
        has_backup=true
    fi

    if [[ "$has_backup" == false ]]; then
        echo "[i] No existing Claude config found — skipping backup"
        return
    fi

    mkdir -p "$BACKUP_DIR"
    local backup_name="claude_conf_${TIMESTAMP}"
    local backup_path="$BACKUP_DIR/$backup_name"

    echo "[...] Backing up to $backup_name.tar.gz"
    tar -czf "${backup_path}.tar.gz" "${files_to_backup[@]}" 2>/dev/null

    if [[ -f "${backup_path}.tar.gz" ]]; then
        local size
        size=$(du -h "${backup_path}.tar.gz" | cut -f1)
        echo "[OK] Backup created: ${backup_path}.tar.gz ($size)"
        echo "     Restore with: tar -xzf ${backup_path}.tar.gz -C $TARGET"
    else
        echo "[!] Backup creation failed (non-fatal, continuing install)"
    fi
}

# ─── Install ──────────────────────────────────────────────────────────────────
install_files() {
    mkdir -p "$TARGET/.claude/agents"
    mkdir -p "$TARGET/.claude/hooks"
    mkdir -p "$TARGET/.claude/rules"
    mkdir -p "$TARGET/.claude/skills/sdlc-workflow"
    mkdir -p "$TARGET/docs/templates"
    mkdir -p "$TARGET/docs/dogmas"

    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
    cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET/.claude/settings.json"
    cp "$SCRIPT_DIR/.claude/agents/"*.md "$TARGET/.claude/agents/"
    cp "$SCRIPT_DIR/.claude/hooks/"* "$TARGET/.claude/hooks/"
    cp "$SCRIPT_DIR/.claude/rules/"*.md "$TARGET/.claude/rules/"
    cp "$SCRIPT_DIR/.claude/skills/sdlc-workflow/SKILL.md" "$TARGET/.claude/skills/sdlc-workflow/"
    cp "$SCRIPT_DIR/templates/context-files/"*-Claude.md "$TARGET/docs/templates/"
    cp -R "$SCRIPT_DIR/docs/dogmas/." "$TARGET/docs/dogmas/"
}

# ─── Verify ───────────────────────────────────────────────────────────────────
verify_install() {
    local ok=true
    for f in \
        CLAUDE.md \
        .claude/settings.json \
        .claude/agents/project-manager.md \
        .claude/hooks/audit-log.sh \
        .claude/hooks/phase-gate.sh \
        .claude/hooks/scope-validator.sh \
        .claude/rules/workflow.md \
        .claude/rules/DOGMAS-CORE.md \
        .claude/rules/DOGMAS-REF-seed.md \
        .claude/skills/sdlc-workflow/SKILL.md \
        docs/templates/PRD-Claude.md \
        docs/templates/SPEC-Claude.md \
        docs/templates/PROJECT_CONTEXT-Claude.md \
        docs/dogmas/DOGMAS.md \
        docs/dogmas/CHECKS/gates.md; do
        if [[ -f "$TARGET/$f" ]]; then
            echo "[OK] $f"
        else
            echo "[FAIL] $f missing"
            ok=false
        fi
    done

    if [[ "$ok" == true ]]; then
        echo ""
        echo "Installation complete. Open Claude Code in $TARGET to start."
    else
        echo ""
        echo "Installation completed with errors. Check missing files above."
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
