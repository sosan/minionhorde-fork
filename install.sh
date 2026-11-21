#!/usr/bin/env bash
#
# minionhorde — Installation Script
# Installs the multi-agent SDLC harness into OpenCode (global, project, or both)
#
# Usage:
#   ./install.sh [global] [project]
#   ./install.sh both
#   ./install.sh          # interactive mode
#
# Examples:
#   ./install.sh global              # install to ~/.config/opencode/
#   ./install.sh project /path/to/project
#   ./install.sh both /path/to/project
#   ./install.sh                     # interactive prompts

set -euo pipefail

# ─── Cyberpunk Color Palette ───────────────────────────────────────────────────
# Neon cyan, magenta, electric yellow, hot pink, acid green, deep purple
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
YELLOW='\033[1;33m'
PINK='\033[0;38;5;206m'
GREEN='\033[0;38;5;82m'
RED='\033[0;38;5;196m'
PURPLE='\033[0;38;5;141m'
WHITE='\033[1;37m'
DIM='\033[2;37m'
NEON='\033[0;38;5;118m'
GLOW='\033[0;38;5;159m'
BG_DARK='\033[48;5;235m'
BG_CYAN='\033[48;5;15m'
RESET='\033[0m'
BOLD='\033[1m'
BLINK='\033[5m'

# ─── Decorative Dividers ───────────────────────────────────────────────────────
print_divider() {
    local color="${1:-$CYAN}"
    echo -e "${color}┌${BG_DARK}${WHITE}────────────────────────────────────────────────────────────────${RESET}${color}┐${RESET}"
}

print_section() {
    local title="$1"
    local color="${2:-$CYAN}"
    echo ""
    echo -e "${color}${BOLD}"
    echo "  +======= $title =======+"
    echo -e "  +======================+${RESET}"
}

print_status() {
    local msg="$1"
    local color="${2:-$GREEN}"
    echo -e "  ${color}[✓]${RESET} ${msg}"
}

print_warning() {
    local msg="$1"
    echo -e "  ${YELLOW}[!]${RESET} ${msg}"
}

print_error() {
    local msg="$1"
    echo -e "  ${RED}[✗]${RESET} ${msg}"
}

print_info() {
    local msg="$1"
    echo -e "  ${DIM}▸${RESET} ${msg}"
}

print_loading() {
    local msg="$1"
    local color="${2:-$CYAN}"
    printf "  ${color}[...]${RESET} %s" "$msg"
    for i in 1 2 3; do
        sleep 0.15
        printf "."
    done
    echo ""
    print_status "$msg" "$color"
}

print_neon_line() {
    local text="$1"
    local color="${2:-$CYAN}"
    local len=60
    local padding=$(( (len - ${#text}) / 2 ))
    local prefix=""
    for ((j=0; j<padding; j++)); do prefix+=" "; done
    echo -e "${BG_DARK}${color}${BOLD}${prefix}${text}${RESET}"
}

# ─── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_AGENTS="$SCRIPT_DIR/agents"
SOURCE_RULES="$SCRIPT_DIR/rules"
SOURCE_COMMANDS="$SCRIPT_DIR/commands"
SOURCE_AGENTS_MD="$SCRIPT_DIR/AGENTS.md"
SOURCE_OPENCODE_CONFIG="$SCRIPT_DIR/templates/opencode-project.json"
SOURCE_GLOBAL_OPENCODE_CONFIG="$SCRIPT_DIR/templates/opencode-global.json"
SOURCE_PLUGINS="$SCRIPT_DIR/plugins"
SOURCE_DOC_TEMPLATES="$SCRIPT_DIR/templates/context-files"
SOURCE_MERGE_CONFIG="$SCRIPT_DIR/scripts/merge_opencode_config.py"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
OPENCODE_GLOBAL="$XDG_CONFIG_HOME/opencode"
OPENCODE_GLOBAL_AGENTS="$OPENCODE_GLOBAL/agents"
OPENCODE_GLOBAL_RULES="$OPENCODE_GLOBAL/rules"
OPENCODE_GLOBAL_COMMANDS="$OPENCODE_GLOBAL/commands"
OPENCODE_GLOBAL_CONFIG="$OPENCODE_GLOBAL/opencode.jsonc"
BACKUP_DIR="$XDG_CONFIG_HOME/opencode_backups"

TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"

# ─── Argument Parsing ──────────────────────────────────────────────────────────
MODE=""
PROJECT_PATH=""

parse_args() {
    if [[ $# -ge 1 ]]; then
        case "$1" in
            global|GLOBAL)
                MODE="global"
                ;;
            project|PROJECT)
                MODE="project"
                if [[ $# -ge 2 ]]; then
                    PROJECT_PATH="$2"
                fi
                ;;
            both|BOTH|all|ALL)
                MODE="both"
                if [[ $# -ge 2 ]]; then
                    PROJECT_PATH="$2"
                fi
                ;;
            *)
                echo -e "${RED}[✗]${RESET} Unknown mode: $1"
                echo -e "${DIM}Usage: $0 [global|project|both] [project_path]${RESET}"
                exit 1
                ;;
        esac
    else
        MODE="interactive"
    fi
}

# ─── Interactive Mode ──────────────────────────────────────────────────────────
interactive_mode() {
    echo ""
    print_section "SELECT INSTALLATION MODE" "$MAGENTA"
    echo ""
    echo -e "  ${DIM}Choose where to deploy the harness:${RESET}"
    echo ""
    echo -e "    ${BOLD}${CYAN}1)${RESET} ${WHITE}Global${RESET}     —  ${DIM}~/.config/opencode/ (all projects on this machine)${RESET}"
    echo -e "    ${BOLD}${CYAN}2)${RESET} ${WHITE}Project${RESET}    —  ${DIM}<project>/.opencode/ (versioned with the repo)${RESET}"
    echo -e "    ${BOLD}${CYAN}3)${RESET} ${WHITE}Both${RESET}       —  ${DIM}Global + Project (recommended)${RESET}"
    echo -e "    ${BOLD}${CYAN}0)${RESET} ${WHITE}Cancel${RESET}"
    echo ""
    printf "  ${GLOW}▸ Choice [1-3]:${RESET} "
    read -r choice

    case "$choice" in
        1) MODE="global" ;;
        2)
            MODE="project"
            printf "  ${GLOW}▸ Project path:${RESET} "
            read -r PROJECT_PATH
            ;;
        3)
            MODE="both"
            printf "  ${GLOW}▸ Project path:${RESET} "
            read -r PROJECT_PATH
            ;;
        0)
            echo -e "\n  ${DIM}▸ Installation cancelled.${RESET}"
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# ─── Validation ────────────────────────────────────────────────────────────────
validate_sources() {
    print_section "VERIFYING SOURCE FILES" "$CYAN"

    local all_ok=true

    if [[ ! -d "$SOURCE_AGENTS" ]]; then
        print_error "Source agents directory not found: $SOURCE_AGENTS"
        all_ok=false
    else
        local count
        count=$(find "$SOURCE_AGENTS" -name "*.md" | wc -l)
        print_status "Found $count agent files in agents/" "$GREEN"
    fi

    if [[ ! -d "$SOURCE_RULES" ]]; then
        print_error "Source rules directory not found: $SOURCE_RULES"
        all_ok=false
    else
        local count
        count=$(find "$SOURCE_RULES" -name "*.md" | wc -l)
        print_status "Found $count rule files in rules/" "$GREEN"
    fi

    if [[ ! -f "$SOURCE_AGENTS_MD" ]]; then
        print_error "Source AGENTS.md not found"
        all_ok=false
    else
        print_status "AGENTS.md constitution found" "$GREEN"
    fi

    if [[ -d "$SOURCE_COMMANDS" ]]; then
        local count
        count=$(find "$SOURCE_COMMANDS" -name "*.md" | wc -l)
        print_status "Found $count command files in commands/" "$GREEN"
    else
        print_error "Source commands directory not found: $SOURCE_COMMANDS"
        all_ok=false
    fi

    for f in "$SOURCE_OPENCODE_CONFIG" "$SOURCE_GLOBAL_OPENCODE_CONFIG" "$SOURCE_MERGE_CONFIG"; do
        if [[ ! -f "$f" ]]; then
            print_error "Missing required file: $f"
            all_ok=false
        fi
    done

    for p in redact instructions guard-audit; do
        if [[ ! -f "$SOURCE_PLUGINS/$p/index.ts" ]]; then
            print_error "Missing plugin: $SOURCE_PLUGINS/$p/index.ts"
            all_ok=false
        fi
    done

    if [[ ! -d "$SOURCE_DOC_TEMPLATES" ]]; then
        print_error "Source document templates not found: $SOURCE_DOC_TEMPLATES"
        all_ok=false
    else
        print_status "Found $(find "$SOURCE_DOC_TEMPLATES" -type f | wc -l) document templates in templates/context-files/" "$GREEN"
    fi

    if [[ "$all_ok" == false ]]; then
        print_error "Source validation failed. Are you running from the repo root?"
        exit 1
    fi

    echo ""
}

validate_project_path() {
    if [[ "$MODE" == "project" || "$MODE" == "both" ]]; then
        if [[ -z "$PROJECT_PATH" ]]; then
            print_error "Project path is required for project installation"
            exit 1
        fi

        if [[ ! -d "$PROJECT_PATH" ]]; then
            print_error "Project directory does not exist: $PROJECT_PATH"
            exit 1
        fi

        # Resolve to absolute path
        PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
        print_status "Project directory: $PROJECT_PATH" "$GREEN"
    fi
}

# ─── Backup ────────────────────────────────────────────────────────────────────
create_backup() {
    if [[ "$MODE" == "project" ]]; then
        return
    fi
    if [[ ! -d "$OPENCODE_GLOBAL" ]]; then
        print_info "No existing OpenCode config found — skipping backup"
        return
    fi

    print_section "CREATING BACKUP" "$YELLOW"

    mkdir -p "$BACKUP_DIR"
    local backup_name="opencode_conf_${TIMESTAMP}"
    local backup_path="$BACKUP_DIR/$backup_name"

    # Check what exists to back up
    local files_to_backup=()
    for dir in "$OPENCODE_GLOBAL_AGENTS" "$OPENCODE_GLOBAL_RULES" "$OPENCODE_GLOBAL_COMMANDS"; do
        if [[ -d "$dir" ]]; then
            files_to_backup+=("$dir")
        fi
    done

    if [[ ${#files_to_backup[@]} -eq 0 ]]; then
        print_info "No existing opencode directories to back up"
        return
    fi

    print_loading "Backing up to $backup_name.tar.gz" "$YELLOW"

    tar -czf "${backup_path}.tar.gz" "${files_to_backup[@]}" 2>/dev/null

    if [[ -f "${backup_path}.tar.gz" ]]; then
        local size
        size=$(du -h "${backup_path}.tar.gz" | cut -f1)
        print_status "Backup created: ${backup_path}.tar.gz ($size)" "$GREEN"
        print_info "Restore with: tar -xzf ${backup_path}.tar.gz -C ~/"
    else
        print_warning "Backup creation failed (non-fatal)"
    fi
}

# ─── Installation Functions ────────────────────────────────────────────────────
install_global() {
    print_section "DEPLOYING TO GLOBAL CONFIG" "$NEON"
    print_neon_line "Target: ~/.config/opencode/" "$PURPLE"
    echo ""

    # Create directories
    for dir in "$OPENCODE_GLOBAL_AGENTS" "$OPENCODE_GLOBAL_RULES" "$OPENCODE_GLOBAL_COMMANDS"; do
        mkdir -p "$dir"
        print_status "Ensured directory: $dir" "$DIM"
    done

    # Copy agents
    print_loading "Deploying agents" "$CYAN"
    cp -f "$SOURCE_AGENTS"/*.md "$OPENCODE_GLOBAL_AGENTS/"
    local agent_count
    agent_count=$(ls "$OPENCODE_GLOBAL_AGENTS"/*.md 2>/dev/null | wc -l)
    print_status "Deployed $agent_count agent files" "$GREEN"

    # Copy rules
    print_loading "Deploying rules" "$MAGENTA"
    cp -f "$SOURCE_RULES"/*.md "$OPENCODE_GLOBAL_RULES/"
    local rule_count
    rule_count=$(ls "$OPENCODE_GLOBAL_RULES"/*.md 2>/dev/null | wc -l)
    print_status "Deployed $rule_count rule files" "$GREEN"

    # Copy constitution
    if [[ -e "$OPENCODE_GLOBAL/AGENTS.md" ]]; then
        print_info "Keeping existing global AGENTS.md"
    else
        cp "$SOURCE_AGENTS_MD" "$OPENCODE_GLOBAL/AGENTS.md"
        print_status "AGENTS.md deployed" "$GREEN"
    fi

    # Copy commands (never overwrite existing)
    for command_file in "$SOURCE_COMMANDS"/*.md; do
        target_command="$OPENCODE_GLOBAL_COMMANDS/$(basename "$command_file")"
        [[ -e "$target_command" ]] || cp "$command_file" "$target_command"
    done
    print_status "Command files deployed without overwriting existing files" "$DIM"

    # Copy document templates (never overwrite existing)
    mkdir -p "$OPENCODE_GLOBAL/templates/context-files"
    for tpl in "$SOURCE_DOC_TEMPLATES"/*; do
        target_tpl="$OPENCODE_GLOBAL/templates/context-files/$(basename "$tpl")"
        [[ -e "$target_tpl" ]] || cp "$tpl" "$target_tpl"
    done
    print_status "Document templates deployed without overwriting existing files" "$DIM"

    # Merge V2 config into whichever global config file already exists (jsonc
    # preferred); both opencode.json and opencode.jsonc merge at runtime, so a
    # user-owned opencode.json is never clobbered.
    if [[ -f "$OPENCODE_GLOBAL/opencode.jsonc" ]]; then
        OPENCODE_GLOBAL_CONFIG="$OPENCODE_GLOBAL/opencode.jsonc"
    elif [[ -f "$OPENCODE_GLOBAL/opencode.json" ]]; then
        OPENCODE_GLOBAL_CONFIG="$OPENCODE_GLOBAL/opencode.json"
    fi
    python3 "$SOURCE_MERGE_CONFIG" \
        "$SOURCE_GLOBAL_OPENCODE_CONFIG" "$OPENCODE_GLOBAL_CONFIG"
    print_status "Merged V2 config into $OPENCODE_GLOBAL_CONFIG" "$GREEN"
    mkdir -p "$OPENCODE_GLOBAL/plugins"
    cp -R "$SOURCE_PLUGINS/redact" "$OPENCODE_GLOBAL/plugins/"
    cp -R "$SOURCE_PLUGINS/instructions" "$OPENCODE_GLOBAL/plugins/"
    cp -R "$SOURCE_PLUGINS/guard-audit" "$OPENCODE_GLOBAL/plugins/"

    echo ""
    print_status "Global installation complete!" "$GREEN"
    echo ""
}

install_project() {
    print_section "DEPLOYING TO PROJECT" "$NEON"
    print_neon_line "Target: $PROJECT_PATH/.opencode/" "$PURPLE"
    echo ""

    local project_opencode="$PROJECT_PATH/.opencode"

    # Create directories
    for dir in "$project_opencode/agents" "$project_opencode/rules" "$project_opencode/commands"; do
        mkdir -p "$dir"
        print_status "Ensured directory: $dir" "$DIM"
    done

    # Copy agents
    print_loading "Deploying agents" "$CYAN"
    cp -f "$SOURCE_AGENTS"/*.md "$project_opencode/agents/"
    local agent_count
    agent_count=$(ls "$project_opencode/agents"/*.md 2>/dev/null | wc -l)
    print_status "Deployed $agent_count agent files" "$GREEN"

    # Copy rules
    print_loading "Deploying rules" "$MAGENTA"
    cp -f "$SOURCE_RULES"/*.md "$project_opencode/rules/"
    local rule_count
    rule_count=$(ls "$project_opencode/rules"/*.md 2>/dev/null | wc -l)
    print_status "Deployed $rule_count rule files" "$GREEN"

    # Copy constitution without overwriting. Relative `rules/` and `agents/`
    # references are rewritten to `.opencode/...`; a path segment already
    # preceded by `/` (e.g. `~/.config/opencode/agents/`) is left untouched.
    print_loading "Deploying AGENTS.md to project root" "$YELLOW"
    if [[ -e "$PROJECT_PATH/AGENTS.md" ]]; then
        print_info "Keeping existing project AGENTS.md"
    else
        sed -e 's#\([^/]\)rules/#\1.opencode/rules/#g' -e 's#^rules/#.opencode/rules/#' \
            -e 's#\([^/]\)agents/#\1.opencode/agents/#g' -e 's#^agents/#.opencode/agents/#' \
            "$SOURCE_AGENTS_MD" > "$PROJECT_PATH/AGENTS.md"
        print_status "Project AGENTS.md deployed with project rule paths" "$GREEN"
    fi

    # Copy commands (never overwrite existing)
    for command_file in "$SOURCE_COMMANDS"/*.md; do
        target_command="$project_opencode/commands/$(basename "$command_file")"
        [[ -e "$target_command" ]] || cp "$command_file" "$target_command"
    done
    print_status "Command files deployed without overwriting existing files" "$DIM"

    # Copy document templates (never overwrite existing; agents reference ./templates/context-files/)
    mkdir -p "$PROJECT_PATH/templates/context-files"
    for tpl in "$SOURCE_DOC_TEMPLATES"/*; do
        target_tpl="$PROJECT_PATH/templates/context-files/$(basename "$tpl")"
        [[ -e "$target_tpl" ]] || cp "$tpl" "$target_tpl"
    done
    print_status "Document templates deployed without overwriting existing files" "$DIM"

    # Project config is the source of truth for project-only installs.
    local project_config="$PROJECT_PATH/opencode.json"
    python3 "$SOURCE_MERGE_CONFIG" \
        "$SOURCE_OPENCODE_CONFIG" "$project_config"
    print_status "Merged V2 config into $project_config" "$GREEN"
    mkdir -p "$project_opencode/plugins"
    cp -R "$SOURCE_PLUGINS/redact" "$project_opencode/plugins/"
    cp -R "$SOURCE_PLUGINS/instructions" "$project_opencode/plugins/"
    cp -R "$SOURCE_PLUGINS/guard-audit" "$project_opencode/plugins/"

    echo ""
    print_status "Project installation complete!" "$GREEN"
    echo ""
}

# ─── Post-Install ──────────────────────────────────────────────────────────────
post_install() {
    print_section "VERIFICATION" "$GREEN"
    echo ""

    # Check global
    if [[ "$MODE" == "global" || "$MODE" == "both" ]]; then
        if [[ -f "$OPENCODE_GLOBAL_AGENTS/project-manager.md" ]]; then
            print_status "Global: project-manager.md verified" "$GREEN"
        else
            print_error "Global: project-manager.md missing!"
        fi

        if [[ -f "$OPENCODE_GLOBAL_RULES/workflow-protocols.md" ]]; then
            print_status "Global: workflow-protocols.md verified" "$GREEN"
        else
            print_error "Global: workflow-protocols.md missing!"
        fi

        if [[ -f "$OPENCODE_GLOBAL/AGENTS.md" ]]; then
            print_status "Global: AGENTS.md verified" "$GREEN"
        else
            print_error "Global: AGENTS.md missing!"
        fi

        if [[ -f "$OPENCODE_GLOBAL_COMMANDS/build.md" ]]; then
            print_status "Global: commands verified" "$GREEN"
        else
            print_error "Global: commands missing!"
        fi

        if grep -q '"default_agent": "project-manager"' "$OPENCODE_GLOBAL_CONFIG"; then
            print_status "Global: V2 config merged ($OPENCODE_GLOBAL_CONFIG)" "$GREEN"
        else
            print_error "Global: V2 config missing default_agent!"
        fi

        if [[ -f "$OPENCODE_GLOBAL/plugins/guard-audit/index.ts" ]]; then
            print_status "Global: guard-audit plugin verified" "$GREEN"
        else
            print_error "Global: guard-audit plugin missing!"
        fi

        if [[ -f "$OPENCODE_GLOBAL/templates/context-files/PRD.md" ]]; then
            print_status "Global: document templates verified" "$GREEN"
        else
            print_error "Global: document templates missing!"
        fi
    fi

    # Check project
    if [[ "$MODE" == "project" || "$MODE" == "both" ]]; then
        if [[ -f "$PROJECT_PATH/.opencode/agents/project-manager.md" ]]; then
            print_status "Project: project-manager.md verified" "$GREEN"
        else
            print_error "Project: project-manager.md missing!"
        fi

        if [[ -f "$PROJECT_PATH/opencode.json" && -f "$PROJECT_PATH/.opencode/rules/security-policy.md" ]]; then
            print_status "Project: V2 config and security instructions verified" "$GREEN"
        else
            print_error "Project: V2 config or security instructions missing!"
        fi
        if [[ -f "$PROJECT_PATH/.opencode/plugins/redact/index.ts" && -f "$PROJECT_PATH/.opencode/plugins/instructions/index.ts" ]]; then
            print_status "Project: V2 plugins verified" "$GREEN"
        else
            print_error "Project: V2 plugins missing!"
        fi
        if [[ -f "$PROJECT_PATH/.opencode/plugins/guard-audit/index.ts" ]]; then
            print_status "Project: guard-audit plugin verified" "$GREEN"
        else
            print_error "Project: guard-audit plugin missing!"
        fi
        if [[ -f "$PROJECT_PATH/.opencode/commands/build.md" ]]; then
            print_status "Project: commands verified" "$GREEN"
        else
            print_error "Project: commands missing!"
        fi
        if [[ -f "$PROJECT_PATH/templates/context-files/PRD.md" ]]; then
            print_status "Project: document templates verified" "$GREEN"
        else
            print_error "Project: document templates missing!"
        fi
        if [[ -f "$PROJECT_PATH/AGENTS.md" ]] && grep -q '.opencode/rules/' "$PROJECT_PATH/AGENTS.md" && ! grep -q '~/.config/opencode/rules/' "$PROJECT_PATH/AGENTS.md"; then
            print_status "Project: AGENTS.md verified with project rule paths" "$GREEN"
        else
            print_error "Project: AGENTS.md missing or rule paths not rewritten!"
        fi
        print_info "guard-audit writes $PROJECT_PATH/.opencode/audit/guard-audit.jsonl — add '.opencode/audit/' to .gitignore"
    fi

    echo ""
}

print_summary() {
    print_section "INSTALLATION SUMMARY" "$GREEN"
    echo ""

    local mode_label
    case "$MODE" in
        global)   mode_label="Global" ;;
        project)  mode_label="Project" ;;
        both)     mode_label="Global + Project" ;;
    esac

    echo -e "  ${BOLD}Mode:${RESET}          $mode_label"
    echo -e "  ${BOLD}Timestamp:${RESET}     $TIMESTAMP"
    if [[ "$MODE" == "global" || "$MODE" == "both" ]]; then
        echo -e "  ${BOLD}Backup:${RESET}         $BACKUP_DIR/opencode_conf_${TIMESTAMP}.tar.gz"
    fi

    if [[ "$MODE" == "global" || "$MODE" == "both" ]]; then
        echo -e "  ${BOLD}Global:${RESET}        $OPENCODE_GLOBAL/"
    fi

    if [[ "$MODE" == "project" || "$MODE" == "both" ]]; then
        echo -e "  ${BOLD}Project:${RESET}       $PROJECT_PATH/.opencode/"
    fi

    echo ""
}

# Helper: create a box line with text centered to $2 chars, colored with $3
make_box_line() {
    local text="$1"
    local width="$2"
    local color="$3"
    local text_len=${#text}
    local pad=$(( width - text_len ))
    [[ $pad -lt 0 ]] && pad=0
    local spaces=""
    for ((j=0; j<pad; j++)); do spaces+=" "; done
    echo -e "  ${DIM}  |  ${color}${text}${spaces}${RESET}${DIM}  |${RESET}"
}

# Helper: create a header line inside the outer box (no extra | wrappers)
make_header_line() {
    local text="$1"
    local width="$2"
    local color="$3"
    local text_len=${#text}
    local pad=$(( width - text_len ))
    [[ $pad -lt 0 ]] && pad=0
    local spaces=""
    for ((j=0; j<pad; j++)); do spaces+=" "; done
    echo -e "|  ${color}${text}${spaces}${RESET}  |"
}

# Build the header with a fixed inner box width
print_header() {
    echo -e "${BG_DARK}${WHITE}"
    local inner_width=66

    echo ""
    make_header_line "+----------------------------------------------------------------+" "$inner_width" "$MAGENTA"
    make_header_line "MINION HORDE" "$inner_width" "$GLOW"
    make_header_line "------------------------------------------------------------------" "$inner_width" "$MAGENTA"
    make_header_line "Multi-Agent SDLC Harness for OpenCode" "$inner_width" "$DIM"
    make_header_line "------------------------------------------------------------------" "$inner_width" "$MAGENTA"
    make_header_line "v2.0" "$inner_width" "$GLOW"
    make_header_line "+----------------------------------------------------------------+" "$inner_width" "$MAGENTA"
    echo ""
}

print_footer() {
    echo ""
    print_neon_line "Installation complete. Next: run 'opencode' and select project-manager" "$GREEN"
    echo ""

    local inner=62  # box width minus "  |" and "|"

    echo -e "  ${DIM}  +----------------------------------------------------------------------+${RESET}"
    make_box_line "Quick Start:" "$inner" "$WHITE"
    echo -e "  ${DIM}  |                                                                      |${RESET}"
    make_box_line "cd your-project" "$inner" "$CYAN"
    make_box_line "opencode" "$inner" "$CYAN"
    make_box_line "→ Tab → select project-manager" "$inner" "$CYAN"
    make_box_line "→ Start your pipeline" "$inner" "$CYAN"
    echo -e "  ${DIM}  |                                                                      |${RESET}"
    make_box_line "Need help?  See README.md or visit opencode.ai/docs" "$inner" "$YELLOW"
    echo -e "  ${DIM}  +----------------------------------------------------------------------+${RESET}"
    echo ""
}

# ─── Main ──────────────────────────────────────────────────────────────────────
main() {
    parse_args "$@"

    if [[ "$MODE" == "interactive" ]]; then
        print_header
        interactive_mode
    fi

    validate_sources
    validate_project_path
    create_backup

    if [[ "$MODE" == "global" || "$MODE" == "both" ]]; then
        install_global
    fi

    if [[ "$MODE" == "project" || "$MODE" == "both" ]]; then
        install_project
    fi

    post_install
    print_summary
    print_footer
}

main "$@"
