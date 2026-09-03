# Installation & Configuration — minionhorde

> **New to OpenCode or MCP?** This guide explains every step from zero to a working harness, including *what each piece is and why you need it*. If you are in a hurry, follow **Prerequisites → Quick Install** and verify with `/mcp`.

---

## 1. Prerequisites

You need these **before** installing the harness. Each is one paragraph with a verify command.

* **OpenCode v1 or v2** — TUI, desktop or IDE extension (VS Code, Cursor, Zed, Windsurf). Any terminal works: WezTerm, Alacritty, Ghostty, Kitty. Verify: `opencode --version` and `opencode tui` (TUI opens, prompt box at bottom).
* **Node.js 18+** — Only required if you install via `npm`/`bun`/`pnpm`/`yarn` or use `npx` for MCP servers (memory, filesystem). Verify: `node -v` should show `v18+`.
* **Git** — Verify: `git --version`.
* **LLM provider API key** — OpenAI, Anthropic, Google, OpenRouter, etc., or local Ollama. OpenCode itself is free; you pay only tokens. Optional global config: `~/.local/share/opencode/auth.json` for credentials.
* **No sudo needed** — Both global (`~/.config/opencode/`) and project (`<project>/.opencode/`) installations write to your home directory or project folder.

---

## 2. What is MCP and Why Does This Harness Need It?

**MCP = Model Context Protocol.** Think of it as **plugins that let the LLM access tools outside chat**: persistent memory, up-to-date docs, or your filesystem. OpenCode's built-in tools (`read`, `glob`, `grep`, `bash`, `task`) handle file work, but **state, parallelism and safety nets rely on MCP servers**.

Without them, Tier 2/3, parallel groups and rollback verification degrade to no-ops (the workflow still runs, but loses cross-session memory and safety checks).

| MCP | Analogy for Juniors | Package / URL | Required? | What You Lose Without It |
|---|---|---|---|---|
| **memory** | **Project hard drive between sessions** — remembers `project_*`, `ticket_*`, `workflow_*` | `npx -y @modelcontextprotocol/server-memory` | **Mandatory** | Tier 2/3 gates fail. PM cannot verify `project_*`/`ticket_*`, parallel `PROJECT_CONTEXT.md` consolidation has no memory. Storage: `MEMORY_FILE_PATH` (`~/.local/share/opencode/memory.jsonl`, local JSONL, no network). |
| **context7** | **Up-to-date Google for docs** — avoids LLM hallucinating old APIs | `https://mcp.context7.com/mcp` (remote) | Recommended | Developer may hallucinate library APIs. Used via `context7_resolve-library-id` + `context7_query-docs`. `enabled: true` by default. Not gating, but saves rework. |
| **filesystem** | **Scoped file reader** — JSON tree / allowed dirs | `npx -y @modelcontextprotocol/server-filesystem` | Optional (fallback) | Nothing if you keep native `read`/`glob`/`grep` (preferred per `rules/workflow-protocols.md`). Only needed for `directory_tree` JSON. |
| **github / gitea** | **PR creator** — turns a fix branch into a pull request | `/home/go/bin/github-mcp-server` or `npx` | Optional | You still get `git push` to `fix/<ticket>-...`; PR creation via `github_*` tools is skipped. Disabled globally by default (`tools.github_*: false`), re-enabled per-agent. Requires `GITHUB_PERSONAL_ACCESS_TOKEN` / `GITEA_ACCESS_TOKEN`. |

**Minimal config that satisfies the harness** — copy into `~/.config/opencode/opencode.jsonc` or `<project>/opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "memory": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
      "enabled": true,
      "environment": {
        "MEMORY_FILE_PATH": "/home/YOU/.local/share/opencode/memory.jsonl"
      }
    },
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp",
      "enabled": true
    },
    "filesystem": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/home/YOU/Projects", "/home/YOU/other-scope"],
      "enabled": true // or false if you rely only on native read/glob
    },
    "github": {
      "type": "local",
      "command": ["/home/YOU/go/bin/github-mcp-server", "stdio"],
      "enabled": false, // enable only if you want PR creation; requires GITHUB_PERSONAL_ACCESS_TOKEN
      "environment": { "GITHUB_PERSONAL_ACCESS_TOKEN": "{env:GITHUB_PERSONAL_ACCESS_TOKEN}" }
    }
  },
  "tools": {
    "github_*": false,  // keep disabled globally; harness re-enables per-agent where needed
    "gitea_*": false
  }
}
```

> **Check:** Inside `opencode` TUI run `/mcp` — you should see `memory: connected`, `context7: connected` (and `filesystem`/`github` if enabled). If `memory` is `disconnected`, all `search_nodes("project_*")` gates will fail — fix `npx` availability (`npm i -g` or `corepack enable`) and `MEMORY_FILE_PATH` writability before running Tier 2/3 or parallel Tier 1.
>
> **Security:** `memory` is low-risk (local JSONL, no FS/network). `filesystem` is medium-risk — scope it to your Projects dir only, never `/`. See `rules/security-policy.md` for blocked files/env/secret patterns that still apply even with MCP.

---

## 3. Install OpenCode

Pick one (same binary):

```bash
# Quick install (macOS / Linux, recommended)
curl -fsSL https://opencode.ai/install | bash

# Node.js (macOS / Linux / Windows)
npm install -g opencode-ai@latest
# or: bun add -g opencode-ai | pnpm add -g opencode-ai | yarn global add opencode-ai

# Homebrew (macOS / Linux, most up-to-date)
brew install anomalyco/tap/opencode
# or: brew install opencode  # official formula, less frequent

# Windows (native)
choco install opencode
scoop install opencode

# Arch
sudo pacman -S opencode            # stable
paru -S opencode-bin               # AUR latest

# Mise / Nix / Docker
mise use -g opencode
nix run nixpkgs#opencode
docker run -it --rm ghcr.io/anomalyco/opencode

# Desktop app (beta)
brew install --cask opencode-desktop  # macOS
# or download: https://opencode.ai/download (dmg / deb / rpm / AppImage)
```

Verify: `opencode --version` and `opencode tui` (TUI opens, prompt box at bottom). Custom binary location without sudo: `OPENCODE_INSTALL_DIR=$HOME/.local/bin curl -fsSL https://opencode.ai/install | bash` (add `~/.local/bin` to `PATH`).

---

## 4. Connect a Provider

```bash
opencode
# inside TUI: /connect → pick provider (Zen recommended for curated coding models, or OpenAI/Anthropic/Gemini/Ollama)
# → opens opencode.ai/auth → sign in, add billing, copy API key → paste in terminal
# credentials stored locally in ~/.local/share/opencode/auth.json
```

Or via env: `export OPENAI_API_KEY=...` / `ANTHROPIC_API_KEY=...` / `GOOGLE_API_KEY=...`.

Global config (optional):

```jsonc
// ~/.config/opencode/opencode.json  (per-user, no sudo)
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/claude-sonnet-4-6",
  "agents": { "project-manager": { "model": "jade/Qwen3.6-35B-A3B" } }
}
```

---

## 5. Install This Workflow

This repository is the **source** of the harness. The files you see here (`agents/`, `AGENTS.md`, `rules/`, `prompts/`) are not yet in the locations where OpenCode discovers them. Installation is simply copying them to where OpenCode looks:

* **Global discovery:** `~/.config/opencode/` — available in every project you open. This is a per-user directory inside your home; no root/sudo needed.
* **Project discovery:** `<project>/.opencode/` + `<project>/AGENTS.md` — available only in that project, versioned with the repo for teams/CI. Project files override globals.

Both can coexist — OpenCode merges them and project wins on conflict.

### Where Files Go (source → destination)

| Source in this repo | Global destination (per-user, no sudo) | Project destination (per-repo, committed) |
|---|---|---|
| `agents/*.md` (7 files) | `~/.config/opencode/agents/*.md` | `<project>/.opencode/agents/*.md` |
| `AGENTS.md` (constitution) | `~/.config/opencode/AGENTS.md` | `<project>/AGENTS.md` (root) |
| `rules/*.md` (protocols + security) | `~/.config/opencode/rules/*.md` | `<project>/rules/*.md` or `<project>/.opencode/rules/*.md` (either works; keep consistent) |
| `prompts/*.md` (optional) | `~/.config/opencode/prompts/*.md` | `<project>/prompts/*.md` |

**Option A — Clone as template (fresh project, simplest):**

```bash
git clone https://github.com/ilgrim/minionhorde.git my-project
cd my-project
# This repo already contains agents/, AGENTS.md, rules/, prompts/ at root for development.
# For a new project you can keep them at root OR move to .opencode:
mkdir -p .opencode/agents .opencode/rules
cp agents/*.md .opencode/agents/
cp AGENTS.md AGENTS.md  # keep at project root — OpenCode also reads ./AGENTS.md
cp rules/*.md .opencode/rules/  # or keep at ./rules/ if you prefer
opencode  # auto-discovers .opencode/agents/project-manager.md as primary
```

**Option B — Add to existing project (project-local, recommended for teams/CI):**

```bash
# From a clone of minionhorde (or from the GitHub release archive)
git clone https://github.com/ilgrim/minionhorde.git /tmp/minionhorde

mkdir -p your-project/.opencode/agents your-project/.opencode/rules
cp /tmp/minionhorde/agents/*.md your-project/.opencode/agents/
cp /tmp/minionhorde/AGENTS.md your-project/AGENTS.md
cp /tmp/minionhorde/rules/*.md your-project/.opencode/rules/
# optional: cp /tmp/minionhorde/prompts/*.md your-project/prompts/
# optional: cp /tmp/minionhorde/opencode.json your-project/opencode.json

cd your-project
opencode
# Tab → select project-manager as entrypoint
```

Commit `AGENTS.md` and `.opencode/` — teammates get the same harness via `git clone`.

**Option C — Install globally (available in every project on this machine, no copy per repo):**

Use this for personal use across many repos. It writes only to your home directory — no system directories, no `sudo`.

```bash
# 1. Clone the harness once to a stable per-user location
git clone https://github.com/ilgrim/minionhorde.git ~/.config/minionhorde
# (any per-user path works — ~/.cache/minionhorde, ~/src/minionhorde, etc.)

# 2. Install agents globally — OpenCode discovers them from any directory you run opencode in
mkdir -p ~/.config/opencode/agents
cp ~/.config/minionhorde/agents/*.md ~/.config/opencode/agents/

# 3. Install shared rules & constitution globally
mkdir -p ~/.config/opencode/rules
cp ~/.config/minionhorde/rules/*.md ~/.config/opencode/rules/
# AGENTS.md is the global constitution — if you already have ~/.config/opencode/AGENTS.md, merge instead of overwriting
cp ~/.config/minionhorde/AGENTS.md ~/.config/opencode/AGENTS.md  # or: diff and merge manually

# 4. (Optional) Set the default agent globally so `opencode` starts with project-manager
# Edit ~/.config/opencode/opencode.json (create if missing):
cat >> ~/.config/opencode/opencode.json <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "project-manager"
}
JSON

# 5. Verify from any project (no project-local files needed)
cd /tmp && opencode
# Inside TUI: /agents → should list project-manager (primary) + architect, developer, test, code-review, devops, documentation

# Keep updated (per-user, no sudo)
cd ~/.config/minionhorde && git pull
cp agents/*.md ~/.config/opencode/agents/
cp rules/*.md ~/.config/opencode/rules/
# if AGENTS.md changed: merge into ~/.config/opencode/AGENTS.md
```

Resulting global layout (all inside your home, no root):

```
~/.config/opencode/          ← per-user config root (no sudo)
├── AGENTS.md                ← global constitution (merged with <project>/AGENTS.md at runtime)
├── agents/
│   ├── project-manager.md   ← primary orchestrator
│   ├── architect.md
│   ├── developer.md
│   ├── test.md
│   ├── code-review.md
│   ├── devops.md
│   └── documentation.md
├── rules/
│   ├── workflow-protocols.md  ← single source of truth
│   └── security-policy.md
└── opencode.json            ← optional global defaults
```

**Global vs project-local — which to choose?**

|  | Project-local (Option B) | Global (Option C) |
|---|---|---|
| **Scope** | Only that repo sees the agents | Every `opencode` session on this machine |
| **Versioning** | Pinned per repo (`git log` shows which harness version) | Single version everywhere (`~/.config/minionhorde` + `git pull`) |
| **Team** | Teammates get it via `git clone` (no extra step) | Each teammate must install globally separately |
| **Override** | `<project>/.opencode/agents/` + `<project>/AGENTS.md` override global | Global is fallback; project can still override |
| **Recommended** | Teams, CI, reproducible builds | Solo / personal machine, many repos |

> **Tip:** Mix both — install globally for personal use, keep project-local copy for CI/team. OpenCode merges them; project-local wins on conflict.
> To uninstall globally (per-user, no sudo): `rm ~/.config/opencode/agents/project-manager.md ~/.config/opencode/agents/architect.md ~/.config/opencode/agents/developer.md ~/.config/opencode/agents/test.md ~/.config/opencode/agents/code-review.md ~/.config/opencode/agents/devops.md ~/.config/opencode/agents/documentation.md; rm ~/.config/opencode/rules/workflow-protocols.md ~/.config/opencode/rules/security-policy.md` and remove `default_agent` from `~/.config/opencode/opencode.json`. Or simply `rm -rf ~/.config/minionhorde` if you only want to stop updating.

**What OpenCode discovers (both scopes):**

* **Project:** `<project>/.opencode/agents/<name>.md` → agent ID `<name>` (e.g. `team/reviewer.md` → `team/reviewer`). Frontmatter `mode`, `model`, `permission`, Markdown body → `system`.
* **Global:** `~/.config/opencode/agents/<name>.md` → same ID, available everywhere (`~/.config/opencode` is per-user, no sudo).

Verify discovery: inside `opencode` TUI, run `/agents` — you should see `project-manager` (primary) + hidden subagents in both scopes.

No other setup needed.

---

## 6. Verify Installation

After installing the harness (any option above):

1. `opencode --version` — should print a version.
2. `opencode` → `/agents` — should list `project-manager` (primary) + 6 subagents.
3. `opencode` → `/mcp` — should show `memory: connected` and `context7: connected` (if enabled). If `memory` is `disconnected`, fix `npx` and `MEMORY_FILE_PATH` before Tier 2/3.
4. `ls ~/.config/opencode/agents/` or `ls .opencode/agents/` — should show 7 `*.md` files.

---

## 7. Troubleshooting

* **Agent not visible in `/agents`:** Check `agents/<name>.md` frontmatter `mode: primary|subagent|all`, `hidden: false`. Path `<project>/.opencode/agents/team/reviewer.md` → ID `team/reviewer`; global `~/.config/opencode/agents/reviewer.md` → ID `reviewer`.
* **`command not found: opencode`:** Fallback path `~/.opencode/bin` not in `PATH`. Add `export PATH="$HOME/.opencode/bin:$PATH"` or use `OPENCODE_INSTALL_DIR=$HOME/.local/bin`.
* **Subagent cannot edit:** Check `permission.edit: allow` + `task: { "subagent-id": allow }` in parent. Last matching rule wins — put `deny *` before `allow <id>`.
* **Tests not created before code:** TDD gate failed — verify `glob tests/<slug>.*` exists before Developer. See `rules/workflow-protocols.md §TDD Protocol Violations`.
* **Rollback fails to find branch:** Check unified naming `backup/pre-<scope>-<timestamp>` where `<scope>` = `phase-<N>` or `group-<letter>` (see `rules/workflow-protocols.md §Rollback §Naming Convention`).
* **`memory: disconnected` in `/mcp`:** Run `npm i -g @modelcontextprotocol/server-memory` or `corepack enable`, check `MEMORY_FILE_PATH` writability, restart `opencode`.

---

*For architecture, tiers and protocol deep dives, see `rules/workflow-protocols.md` (single source of truth) and `AGENTS.md`.*
