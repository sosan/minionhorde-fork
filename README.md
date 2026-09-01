# minionhorde — (Almost) Enterprise Multi-Agent SDLC Harness for OpenCode

> **LLM harness for OpenCode that implements a full SDLC with strong quality gates.** A supervisor-worker orchestration that turns a single prompt into PRD → specs → planning → TDD → implementation → tests → review → docs → git, with tier-aware activation and hybrid safety nets.

[![Certified Shovelware](https://justin.searls.co/img/shovelware.svg)](https://justin.searls.co/shovelware/)
[![OpenCode](https://img.shields.io/badge/OpenCode-v1%2B%20%7C%20v2-blue)](https://opencode.ai/docs)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Workflow](https://img.shields.io/badge/workflow-Tier%200--3-orange)](#tiers)

## What is this?

**minionhorde** is not an application — it is a **configuration-only control plane for OpenCode**. It replaces the single `build` agent with a governed pipeline:

* **One primary orchestrator** (`project-manager`) that never writes code — only triages, routes, checks gates and consolidates.
* **Six hidden subagents** (`architect`, `developer`, `test`, `code-review`, `devops`, `documentation`) invoked via `task` in parallel where safe.
* **Three tiers** (`Tier 0 direct`, `Tier 1 new-project`, `Tier 2 feature`, `Tier 3 bugfix`) with size-aware activation (Small/Medium/Large) and pruned artefacts.
* **Gates, not vibes:** every handoff is a `File Integrity Checkpoint` (`glob` + `content >0`) with retry → recovery → escalation. TDD is mandatory (`AC-N → TC-00N`, red → green).

Inspired by supervisor-worker patterns from `anomalyco/opencode`, `nadimnesar/agentic-workflow` and `ABIvan-Tech/opencode-agentic-workflows`, but tier-aware and pruned for real projects (3 sources in Small vs 6 in Large).

This repository is the **source** of the harness. The files you see at the repo root (`agents/`, `AGENTS.md`, `rules/`, `prompts/`) are the source artefacts. When you install the harness, they are copied into the locations where OpenCode actually discovers them (see Installation).

## Why not a single agent?

| Single `build` agent | minionhorde pipeline |
|---|---|
| Planning, coding, testing and review bleed together | Role separation → narrow prompts, consistent output |
| Chat history as handoff | `docs/specs/*.md` + `docs/PROJECT_CONTEXT.md` + `audit_*` as handoff (deterministic, debuggable) |
| One model, one temperature | Per-agent `model`/`temperature`/`steps` (e.g. `architect 0.3/30`, `developer 0.2/150`) |
| Permissions all-open | Path-scoped `edit: allow/deny`, `bash: ask`, `task: allowlist` |

## Architecture

```
User prompt
   │
   ▼
project-manager (primary, never writes code)
   │  Mode: new-project / add-feature / fix-bug / direct-response (Tier 0)
   │  Phase 0: Complexity Assessment (Small/Medium/Large + Low/Medium/High risk)
   ├─► Phase 1: PRD + specs/*.md (GIVEN/WHEN/THEN, AC-N)  ──► Phase 1b: Test TDD stubs (1 AC→1 TC, FAIL)
   ├─► Phase 2: Architect PLANNING.md + ROADMAP.md (Parallel group: A/B + status)  [Medium/Large only; Small skip]
   ├─► Phase 3: Developer by Parallel group (N task in 1 message) ──► Test validate (max 3) ──► clean stash/branch
   ├─► Phase 4: Code Review (Critical/High/Medium loop max 5/3, Low → incident_*)
   ├─► Phase 5: Documentation specs sync (incremental: glob + git diff --name-only guard)
   └─► Phase 6: DevOps git add/commit/push + CHANGELOG derived (strictly AFTER docs)
           │
           ▼
     docs/ + memory graph (audit_*, implementation_*, decision_*, project_*/ticket_*/root_cause_*)
```

**Key invariants (see `rules/workflow-protocols.md` — single source of truth):**

* **TDD Protocol:** `Spec (AC-N) → Test (TC-00N, FAIL) → Code (make tests PASS) → Test validates`. Developer never starts without `glob tests/<slug>.*`.
* **Parallelization Protocol:** `IMPLEMENTATION_ROADMAP.md` marks `Parallel group: <letter>`. PM launches all phases in same group in **one message** (`N task` calls), waits, consolidates `PROJECT_CONTEXT.md` once.
* **Rollback Protocol (Hybrid):** `stash` fast (`pop --index`) + `branch` hard (`reset --hard backup/pre-<scope>-<timestamp>`) with unified naming `pre-<scope>` = `phase-<N>` (sequential) or `group-<letter>` (parallel). Both verified before advancing.
* **File Integrity Checkpoints:** `Verify BEFORE (prereqs via glob)` → delegate → `Verify AFTER (deliverable content >0)` → recovery → escalation after 2 fails.
* **Delegation Prompt Template (mandatory):** every `task` pastes `agents/<agent>.md` + `rules/workflow-protocols.md §…` excerpt + `Required Skills — On Demand` (1-2 max, e.g. `python-enterprise`) + `specs` content + `Verify BEFORE/AFTER` globs + `Output Contract`.

### Agents

| Agent | Source file | Mode | Model | Steps | Role | Owns |
|---|---|---|---|---|---|---|
| **project-manager** | `agents/project-manager.md` | `primary` | `jade/Qwen3.6-35B-A3B` | 60 | Supervisor, tier detection, gatekeeper | `docs/PRD.md`, `docs/specs/*`, `project_*`, `ticket_*`, `workflow_*` |
| **architect** | `agents/architect.md` | `subagent` | `jade/Qwen3.8-27B` | 30 | Tech planning, `PLANNING.md`, `specs/<feature>.md` | `docs/PLANNING.md`, `decision_*` |
| **developer** | `agents/developer.md` | `subagent` | `jade/Qwen3.8-27B` | 150 | Tier-aware implementation, docstrings, `PROJECT_CONTEXT.md` | `src/*`, `implementation_*`, `root_cause_*` |
| **test** | `agents/test.md` | `subagent` | `jade/Qwen3.8-27B` | 35 | TDD stubs + execution + regression + coverage >85% | `tests/*` |
| **code-review** | `agents/code-review.md` | `subagent` | `jade/Qwen3.8-27B` | 25 | Quality + security, `Critical>High>Medium>Low>Suggestion` → `incident_*` | `incident_*` |
| **devops** | `agents/devops.md` | `subagent` | `jade/Qwen3.8-27B` | 20 | Git (conventional commits), `CHANGELOG.md` derived, CI/CD (Large) | `docs/CHANGELOG.md` |
| **documentation** | `agents/documentation.md` | `subagent` | `jade/Qwen3.8-27B` | 20 | Specs sync incremental + `README/API_REFERENCE` (Large) | `docs/README.md`, `docs/API_REFERENCE.md` |

Permissions enforce safety: `architect`/`test`/`code-review` `bash: deny` except test runners; `devops` `bash: ask`; `project-manager` `task: allowlist (architect, developer, test, code-review, devops, documentation, explore)`.

### Tiers

| Tier | Trigger | Activation | Artefacts (pruned) |
|---|---|---|---|
| **Tier 0 direct** | `≤3 files`, no deps, no API/auth/db change, or flag `direct/rápido` | PM + Developer + DevOps (minimal), Test optional | **0 docs** — direct code + `CHANGELOG` derived |
| **Tier 1 Small** | New project `<5 files` | PM + Developer + Test, skip Architect/CR, DevOps/Doc minimal | `PRD.md + specs + PROJECT_CONTEXT.md` (3, no PLANNING/ROADMAP) |
| **Tier 1 Medium** | 5–20 files | + Architect + CR | + `PLANNING.md` + `ROADMAP(status)` |
| **Tier 1 Large** | >20 files | All agents full | + `README.md` + `API_REFERENCE.md` + `CHANGELOG.md` + CI/CD |
| **Tier 2 Feature** | `add/feature/extend` on existing project | PM + Architect + Developer + Test + CR + DevOps/Doc minimal | `specs/<feature>.md` + `PROJECT_CONTEXT.md` |
| **Tier 3 Bug** | `fix/bug #N` | PM + Developer + Test + CR, Architect if unclear | `ticket_*` + `root_cause_*` + bug-repro test (Developer creates) |

See `rules/workflow-protocols.md §Document Ownership Map` and `§Prerequisite & Deliverable Table` for canonical gates (pruned notes included).

## Installation

### Prerequisites

* **OpenCode v1+ or v2** — TUI, desktop or IDE extension (VS Code, Cursor, Zed, Windsurf). Any terminal: WezTerm, Alacritty, Ghostty, Kitty recommended.
* **Node.js 18+** only if installing via `npm`/`bun`/`pnpm`/`yarn` or if you use `npx` for MCP servers (memory, filesystem).
* **Git**.
* **LLM provider API key** (OpenAI, Anthropic, Google, OpenRouter, etc.) or local Ollama. OpenCode itself is free; you pay only tokens.
* Optional: `~/.config/opencode` for global config, `~/.local/share/opencode/auth.json` for credentials.

No administrator privileges are required at any point — both global and project installations write to your home directory (`~/.config/opencode/`) or to the project folder itself. Never use `sudo` for this harness.

### MCP Requirements (mandatory for this workflow)

This harness is **MCP-dependent**. OpenCode's built-in tools (`read`, `glob`, `grep`, `bash`, `task`) are enough for file work, but the workflow's state, parallelism and safety nets rely on external MCP servers. Without them, Tier 2/3, parallel groups and rollback verification degrade to no-ops.

| MCP | Package / URL | Required? | Why this workflow needs it |
|---|---|---|---|
| **memory** | `npx -y @modelcontextprotocol/server-memory` | **Mandatory** | Persistent Knowledge Graph between sessions. Stores `project_*` (Tier 2), `ticket_*`/`root_cause_*` (Tier 3), `workflow_*` (phase + `pre-<scope>` stash/branch refs), `decision_*` (Architect), `implementation_*`/`audit_*`/`incident_*` (gates, timings, rollback refs). All agents use `create_entities`, `search_nodes`, `open_nodes`, `add_observations`. Without it, PM cannot verify `project_*`/`ticket_*` gates and parallel `PROJECT_CONTEXT.md` consolidation has no memory. Storage: `MEMORY_FILE_PATH` (`~/.local/share/opencode/memory.jsonl` by default, local JSONL, no network). |
| **context7** | `https://mcp.context7.com/mcp` (remote) | Recommended | Up-to-date library/framework docs for Developer. Used via `context7_resolve-library-id` + `context7_query-docs` before implementing (avoids stale training data). Not gating, but saves hallucinations. `enabled: true` by default. |
| **filesystem** | `npx -y @modelcontextprotocol/server-filesystem` | Optional (fallback) | Scoped FS `read_file`, `write_file`, `list_directory`, `search_files`. Native `read`/`glob`/`grep` are preferred per `Tool preference` (`rules/workflow-protocols.md` dogma) — `filesystem` is only for `directory_tree` JSON or `allowed_directories` checks. If you keep native preference, you can leave it disabled. |
| **github / gitea** | `/home/go/bin/github-mcp-server`, `/home/go/bin/gitea-mcp` (or `npx`) | Optional | PR/issue integration. `project-manager` Phase 5 `fix #N` creates branch `fix/<ticket>-...` + push; with `github` MCP it can also open a PR via `github_*` tools. Disabled globally by default (`tools.github_*: false`), re-enabled per-agent via `agents/project-manager.md`/`devops.md` frontmatter `tools` allowlist. Requires `GITHUB_PERSONAL_ACCESS_TOKEN` / `GITEA_ACCESS_TOKEN` env. |

**Minimal config that satisfies the harness (copy into `~/.config/opencode/opencode.jsonc` or `<project>/opencode.jsonc`):**

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

### 1. Install OpenCode

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

### 2. Connect a provider

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

### 3. Install this workflow

This repository is the **source** of the harness. The files you see here (`agents/`, `AGENTS.md`, `rules/`, `prompts/`) are not yet in the locations where OpenCode discovers them. Installation is simply copying them to where OpenCode looks:

* **Global discovery:** `~/.config/opencode/` — available in every project you open. This is a per-user directory inside your home; no root/sudo needed.
* **Project discovery:** `<project>/.opencode/` + `<project>/AGENTS.md` — available only in that project, versioned with the repo for teams/CI. Project files override globals.

Both can coexist — OpenCode merges them and project wins on conflict.

#### Where files go (source → destination)

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

## Usage

### The 30-second flow

```bash
cd your-project
opencode
# Tab → select project-manager (primary)
# prompt: "Build me a REST API for task management"
# → PM asks 3 complexity questions → you answer → PM creates PRD + specs → Test creates stubs (FAIL) → Architect PLANNING + ROADMAP → Developer by Parallel group → Test validates → CR → Docs specs sync → DevOps commit
```

### Tier-aware examples

```bash
# Tier 0 — trivial, no pipeline
opencode run --agent project-manager "corrige el typo en src/main.py"
# → PM detects ≤3 files, asks via question tool: "¿Direct mode?" → Yes → Developer direct + DevOps commit

# Tier 1 Small — no PLANNING overhead
"Build a Go CLI that converts CSV to JSON (3 files)"
# → PRD + specs/<csv>.md → tests stub → Developer (1 group) → docs specs sync (if changed) → DevOps

# Tier 2 — feature on existing project
"Add OAuth2 token refresh to my existing API (in my project)"
# → glob src/**/*, project_* entity → Architect specs/<oauth-refresh>.md → tests → Developer respects patterns → Test regression → CR → Docs → DevOps feature/<oauth-refresh>

# Tier 3 — bug
"Fix the token refresh race #142"
# → ticket_142_* → Developer root_cause_142_* (file:line + hypothesis) → bug-repro test (FAIL→PASS) → minimal fix → Test regression → CR quick → DevOps fix(auth): ... #142
```

### Key files (where to look when debugging)

* `AGENTS.md` — Global coding preferences, language guard, security policy, tier detection, feedback loops (source for PM).
* `rules/workflow-protocols.md` — **Single source of truth** for `TDD Protocol`, `File Integrity Checkpoints`, `Parallelization Protocol`, `Rollback Protocol (stash+branch pre-<scope>)`, `Memory MCP Protocol`, `Document Ownership Map`. Do not duplicate.
* `rules/security-policy.md` — Blocked files/env/commands/secret patterns (mandatory).
* `agents/*.md` — Per-agent system prompts, tier awareness, `tool preference` (native `glob/read/grep` primary), `steps`, `temperature`, `model`.
* `docs/` — Generated at runtime: `PRD.md`, `specs/*.md` (AC-N G/W/T), `PLANNING.md`, `IMPLEMENTATION_ROADMAP.md` (with `Parallel group: A/B` + `status`), `PROJECT_CONTEXT.md` (living state), `CHANGELOG.md` (derived), `README.md`, `API_REFERENCE.md`.
* `prompts/build.txt` + `plan.txt` — Built-in `build` (full-access) / `plan` (restricted) primaries you can `Tab` to.

## Project Structure

```
minionhorde/                 ← source repo (what you clone)
├── AGENTS.md                ← source constitution → installed to ~/.config/opencode/AGENTS.md or <project>/AGENTS.md
├── agents/                  ← source agents → installed to ~/.config/opencode/agents/ or <project>/.opencode/agents/
│   ├── project-manager.md
│   ├── architect.md
│   ├── developer.md
│   ├── test.md
│   ├── code-review.md
│   ├── devops.md
│   └── documentation.md
├── rules/                   ← source rules → installed to ~/.config/opencode/rules/ or <project>/.opencode/rules/
│   ├── workflow-protocols.md
│   └── security-policy.md
├── prompts/
│   ├── build.txt
│   └── plan.txt
├── opencode.json            ← optional project OpenCode config (agents, permissions, default_agent)
├── LICENSE
└── README.md
```

When installed, OpenCode resolves:
* **Global:** `~/.config/opencode/AGENTS.md` + `~/.config/opencode/agents/*.md` + `~/.config/opencode/rules/*.md` (per-user, no sudo)
* **Project:** `<project>/AGENTS.md` + `<project>/.opencode/agents/*.md` + `<project>/.opencode/rules/*.md` (project wins on conflict)

## Protocols (deep dive)

* **Delegation Prompt Template (mandatory):** Every `task` pastes `agents/<agent>.md` + `rules/workflow-protocols.md §…` excerpt + `Required Skills — On Demand` (e.g. `python-enterprise` only for Python stack) + `specs` content + `Verify BEFORE/AFTER globs` + `Output Contract`. Prevents degraded subagent.
* **Tool preference:** Native `read`/`glob`/`grep` for gates, `filesystem` MCP only for `directory_tree`/`allowed_directories`. Batch independent `glob`s in parallel, use `docs/specs/*.md` not `**/*`, cache per phase.
* **Memory MCP:** `project_*`, `workflow_*`, `ticket_*`, `decision_*`, `implementation_*`, `root_cause_*`, `incident_*`, `audit_*` — see `rules/... §Memory MCP Protocol` for creation/ownership/timing. Never `read_graph`.

## Troubleshooting

* **Agent not visible in `/agents`:** Check `agents/<name>.md` frontmatter `mode: primary|subagent|all`, `hidden: false`. Path `<project>/.opencode/agents/team/reviewer.md` → ID `team/reviewer`; global `~/.config/opencode/agents/reviewer.md` → ID `reviewer`.
* **`command not found: opencode`:** Fallback path `~/.opencode/bin` not in `PATH`. Add `export PATH="$HOME/.opencode/bin:$PATH"` or use `OPENCODE_INSTALL_DIR=$HOME/.local/bin`.
* **Subagent cannot edit:** Check `permission.edit: allow` + `task: { "subagent-id": allow }` in parent. Last matching rule wins — put `deny *` before `allow <id>`.
* **Tests not created before code:** TDD gate failed — verify `glob tests/<slug>.*` exists before Developer. See `§TDD Protocol Violations`.
* **Rollback fails to find branch:** Check unified naming `backup/pre-<scope>-<timestamp>` where `<scope>` = `phase-<N>` or `group-<letter>` (see `§Rollback §Naming Convention`).

## Contributing

PRs welcome. Keep tier-aware pruning: don't add artefacts for Tier 0/Small, keep `rules/workflow-protocols.md` as single source of truth, respect `security-policy.md` (never read `.env`, tokens, keys).

## License

MIT — see `LICENSE`.

---

*Built for OpenCode. Tested with OpenCode v1 TUI + desktop + VS Code extension. For OpenCode docs: `opencode.ai/docs`, `opencode.ai/docs/agents`, `opencode.ai/docs/permissions`, `opencode.ai/docs/config`.*
