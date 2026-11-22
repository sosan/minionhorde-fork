# minionhorde — (Almost) Enterprise Multi-Agent SDLC Harness for OpenCode

> **LLM harness for OpenCode that implements a full SDLC with strong quality gates.** A supervisor-worker orchestration that turns a single prompt into PRD → specs → planning → TDD → implementation → tests → review → docs → git, with tier-aware activation and hybrid safety nets.

[![Certified Shovelware](https://justin.searls.co/img/shovelware.svg)](https://justin.searls.co/shovelware/)
[![OpenCode](https://img.shields.io/badge/OpenCode-v2.3.2%2B-blue)](https://opencode.ai/docs)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Workflow](https://img.shields.io/badge/workflow-Tier%200--3-orange)](#tiers)

## What is this?

**minionhorde** is not an application — it is a **configuration-only control plane for OpenCode**. It replaces the single `build` agent with a governed pipeline:

* **One primary orchestrator** (`project-manager`) that never writes code — only triages, routes, checks gates and consolidates.
* **Six hidden subagents** (`architect`, `developer`, `test`, `code-review`, `devops`, `documentation`) invoked via `subagent` in parallel where safe.
* **Three tiers** (`Tier 0 direct`, `Tier 1 new-project`, `Tier 2 feature`, `Tier 3 bugfix`) with size-aware activation (Small/Medium/Large) and pruned artefacts.
* **Gates, not vibes:** every handoff is a `File Integrity Checkpoint` (`glob` + `content >0`) with retry → recovery → escalation. TDD is mandatory (`AC-N → TC-00N`, red → green).

Inspired by supervisor-worker patterns from `anomalyco/opencode`, `nadimnesar/agentic-workflow` and `ABIvan-Tech/opencode-agentic-workflows`, but tier-aware and pruned for real projects (3 sources in Small vs 6 in Large).

This repository is the **source** of the harness. The files you see at the repo root (`agents/`, `AGENTS.md`, `rules/`, `commands/`, `plugins/`, `templates/`) are the source artefacts. When you install the harness, they are copied into the locations where OpenCode actually discovers them (see Installation).

## Why not a single agent?

| Single `build` agent | minionhorde pipeline |
|---|---|
| Planning, coding, testing and review bleed together | Role separation → narrow prompts, consistent output |
| Chat history as handoff | `docs/specs/*.md` + `docs/PROJECT_CONTEXT.md` + `audit_*` as handoff (deterministic, debuggable) |
| One model, one step budget | Per-agent `model`/`steps` (e.g. `architect 30`, `developer 150`) |
| Permissions all-open | Path-scoped `edit: allow/deny`, `shell: ask`, `subagent: allowlist` |

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
   ├─► Phase 3: Developer by Parallel group (N subagent calls in 1 message) ──► Test validate (max 3) ──► clean stash/branch
   ├─► Phase 4: Code Review (Critical/High/Medium loop max 5/3, Low → incident_*)
   ├─► Phase 5: Documentation specs sync (incremental: glob + git diff --name-only guard)
   └─► Phase 6: DevOps git add/commit/push + CHANGELOG derived (strictly AFTER docs)
           │
           ▼
     docs/ + memory graph (audit_*, implementation_*, decision_*, project_*/ticket_*/root_cause_*)
```

**Key invariants (see `rules/workflow-protocols.md` — single source of truth):**

* **TDD Protocol:** `Spec (AC-N) → Test (TC-00N, FAIL) → Code (make tests PASS) → Test validates`. Developer never starts without `glob tests/<slug>.*`.
* **Parallelization Protocol:** `IMPLEMENTATION_ROADMAP.md` marks `Parallel group: <letter>`. PM launches all phases in same group in **one message** (`N subagent` calls), waits, consolidates `PROJECT_CONTEXT.md` once.
* **Rollback Protocol (Hybrid):** `stash` fast (`pop --index`) + `branch` hard (`reset --hard backup/pre-<scope>-<timestamp>`) with unified naming `pre-<scope>` = `phase-<N>` (sequential) or `group-<letter>` (parallel). Both verified before advancing.
* **File Integrity Checkpoints:** `Verify BEFORE (prereqs via glob)` → delegate → `Verify AFTER (deliverable content >0)` → recovery → escalation after 2 fails.
* **Delegation Prompt Template (mandatory):** every `subagent` call pastes `rules/workflow-protocols.md §…` excerpt + `Required Skills — On Demand` (1-2 max, e.g. `python-enterprise`) + `specs` content + `Verify BEFORE/AFTER` globs + `Output Contract`. Agent system prompts are loaded automatically by OpenCode — do NOT paste `agents/<agent>.md` (redundant, wastes ~4.5k tokens).

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

Permissions enforce safety: `architect`/`test`/`code-review` `shell: deny` except test runners; `devops` `shell: ask`; `project-manager` `subagent: allowlist (architect, developer, test, code-review, devops, documentation, explore)`.

### Tiers

| Tier | Trigger | Activation | Artefacts (pruned) |
|---|---|---|---|
| **Tier 0 direct** | `≤3 files`, no deps, no API/auth/db change, or flag `direct/rápido` | PM + Developer + DevOps (minimal), Test optional | **0 docs** — direct code + `CHANGELOG` derived |
| **Tier 1 Small** | New project `<5 files` | PM + Developer + Test, skip Architect/CR, DevOps/Doc minimal | `PRD.md + specs + PROJECT_CONTEXT.md` (3, no PLANNING/ROADMAP) |
| **Tier 1 Medium** | 5–20 files | + Architect + CR | + `PLANNING.md` + `ROADMAP(status)` |
| **Tier 1 Large** | >20 files | All agents full | + `README.md` + `API_REFERENCE.md` + `CHANGELOG.md` + CI/CD |
| **Tier 2 Feature** | `add/feature/extend` on existing project | PM + Architect + Developer + Test + CR + DevOps/Doc minimal | `specs/<feature>.md` + `PROJECT_CONTEXT.md` |
| **Tier 3 Bug** | `fix/bug #N` | PM + Developer + Test + CR, Architect if unclear | `ticket_*` + `root_cause_*` + bug-repro test (Developer creates) |
| **Tier 4 Research** | `spike/research/explore/POC/feasibility` | PM + Architect (50 steps) + Developer (POC) + Documentation | `docs/spikes/<topic>-brief.md` + `docs/spikes/<topic>-<date>.md` + `decision_*` entity |

See `rules/workflow-protocols.md §Document Ownership Map` and `§Prerequisite & Deliverable Table` for canonical gates (pruned notes included).

## Installation

### Prerequisites

* **OpenCode v2.3.2+** — TUI, desktop or IDE extension (VS Code, Cursor, Zed, Windsurf). Any terminal: WezTerm, Alacritty, Ghostty, Kitty recommended. (V1 is not supported: V2 renamed `task`→`subagent`, dropped `rules/` auto-discovery, and moved hooks to the plugin API.)
* **Node.js 18+** only if installing via `npm`/`bun`/`pnpm`/`yarn` or if you use `npx` for MCP servers (memory, filesystem).
* **Git**.
* **LLM provider API key** (OpenAI, Anthropic, Google, OpenRouter, etc.) or local Ollama. OpenCode itself is free; you pay only tokens.
* Optional: `~/.config/opencode` for global config, `~/.local/share/opencode/auth.json` for credentials.

No administrator privileges are required at any point — both global and project installations write to your home directory (`~/.config/opencode/`) or to the project folder itself. Never use `sudo` for this harness.

### MCP Requirements (mandatory for this workflow)

This harness is **MCP-dependent**. OpenCode's built-in tools (`read`, `glob`, `grep`, `shell`, `subagent`) are enough for file work, but the workflow's state, parallelism and safety nets rely on external MCP servers. Without them, Tier 2/3, parallel groups and rollback verification degrade to no-ops.

| MCP | Package / URL | Required? | Why this workflow needs it |
|---|---|---|---|
| **memory** | `npx -y @modelcontextprotocol/server-memory` | **Mandatory** | Persistent Knowledge Graph between sessions. Stores `project_*` (Tier 2), `ticket_*`/`root_cause_*` (Tier 3), `workflow_*` (phase + `pre-<scope>` stash/branch refs), `decision_*` (Architect), `implementation_*`/`audit_*`/`incident_*` (gates, timings, rollback refs). All agents use `create_entities`, `search_nodes`, `open_nodes`, `add_observations`. Without it, PM cannot verify `project_*`/`ticket_*` gates and parallel `PROJECT_CONTEXT.md` consolidation has no memory. Storage: `MEMORY_FILE_PATH` (`~/.local/share/opencode/memory.jsonl` by default, local JSONL, no network). |
| **context7** | `https://mcp.context7.com/mcp` (remote) | Recommended | Up-to-date library/framework docs for Developer. Used via `context7_resolve-library-id` + `context7_query-docs` before implementing (avoids stale training data). Not gating, but saves hallucinations. `enabled: true` by default. |
| **filesystem** | `npx -y @modelcontextprotocol/server-filesystem` | Optional (fallback) | Scoped FS `read_file`, `write_file`, `list_directory`, `search_files`. Native `read`/`glob`/`grep` are preferred per `Tool preference` (`rules/workflow-protocols.md` dogma) — `filesystem` is only for `directory_tree` JSON or `allowed_directories` checks. If you keep native preference, you can leave it disabled. |
| **github / gitea** | `/home/go/bin/github-mcp-server`, `/home/go/bin/gitea-mcp` (or `npx`) | Optional | PR/issue integration. `project-manager` Phase 5 `fix #N` creates branch `fix/<ticket>-...` + push; with `github` MCP it can also open a PR via `github_*` tools. Disabled globally by default (`tools.github_*: false`), re-enabled per-agent via `agents/project-manager.md`/`devops.md` frontmatter `tools` allowlist. Requires `GITHUB_PERSONAL_ACCESS_TOKEN` / `GITEA_ACCESS_TOKEN` env. |

**Minimal config that satisfies the harness** — `install.sh` merges this into `~/.config/opencode/opencode.json(c)` (global) or `<project>/opencode.json` (project) without touching your own keys. Source templates: `templates/opencode-global.json` and `templates/opencode-project.json`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "project-manager",
  // V2 does NOT auto-discover rules/ — instruction files must be listed here.
  "instructions": [".opencode/rules/security-policy.md"], // project; global uses "rules/security-policy.md"
  "experimental": {
    "todo": true,          // todowrite tool for every agent
    "subagent_depth": 2    // PM -> subagent -> subagent (nested delegation)
  },
  "permissions": [
    {"action": "external_directory", "resource": "*", "effect": "ask"},
    {"action": "read", "resource": "*.env", "effect": "ask"},
    {"action": "read", "resource": "*.env.*", "effect": "ask"},
    {"action": "read", "resource": "*.env.example", "effect": "allow"},
    {"action": "shell", "resource": "sudo *", "effect": "ask"},
    {"action": "shell", "resource": "rm -rf *", "effect": "ask"},
    {"action": "shell", "resource": "git push --force*", "effect": "ask"}  // guard-audit escalates ask→deny and audits it
  ],
  "mcp": {
    "servers": {
      "memory": {
        "type": "local",
        "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        "environment": { "MEMORY_FILE_PATH": "{env:HOME}/.local/share/opencode/memory.jsonl" }
      },
      "context7": { "type": "remote", "url": "https://mcp.context7.com/mcp" }
    }
  },
  "plugins": [
    "./.opencode/plugins/redact",       // scrubs secrets from prompts/requests/tool input
    "./.opencode/plugins/instructions", // shrinks the <env> system block to Platform only
    "./.opencode/plugins/guard-audit"   // denies dangerous shell + hash-chained audit log
  ]
}
```

Notes:
- `rules/workflow-protocols.md` (39 KB) is deliberately **not** in `instructions` — it would be re-sent on every request. Agents read it on demand with the `read` tool when a protocol section is needed; only `security-policy.md` is always loaded.
 - **guard-audit layering:** shell rules use `ask` (not `deny`) so the plugin's `permission.hook("evaluate")` runs, escalates dangerous commands to `deny`, and writes a `status:"denied"` entry to `<project>/.opencode/audit/guard-audit.jsonl` (hash-chained, redacted; verify with `verifyAudit`). A configured `deny` is final and skips the hook, so it would **not** be audited. The log only records events that reach a hook (tool execute, shell create, permission evaluate) — if the model refuses in plain text without calling the shell tool, nothing is logged; that block is behavioral (AGENTS.md), not mechanical. Auditing refused-in-text attempts would need `session.hook("prompt")` scanning user messages — noisy (false positives), not enabled by default.
- Optional MCP servers (filesystem, github) go under `mcp.servers` with `"enabled": false`; V2 has no top-level `tools:` kill-switch — disable MCP tools per server or via `permissions`/`policies`.

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

This repository is the **source** of the harness. `install.sh` copies the artefacts to where OpenCode V2 actually discovers them and merges the V2 config (never overwriting your own keys):

```bash
git clone https://github.com/ilgrim/minionhorde.git /tmp/minionhorde
cd /tmp/minionhorde

./install.sh project /path/to/your-project   # project-local (recommended for teams/CI)
./install.sh global                           # every project on this machine (~/.config/opencode, no sudo)
./install.sh both /path/to/your-project       # global + project
./install.sh                                  # interactive mode
```

* **Global discovery:** `~/.config/opencode/` — available in every project you open. Per-user directory inside your home; no root/sudo needed. Existing `opencode.json`/`opencode.jsonc` are merged, not replaced; a timestamped backup of `agents/`, `rules/`, `commands/` goes to `~/.config/opencode_backups/`.
* **Project discovery:** `<project>/.opencode/` + `<project>/AGENTS.md` + `<project>/opencode.json` — versioned with the repo for teams/CI. Project files override globals.

Both can coexist — OpenCode merges them and project wins on conflict.

#### Where files go (source → destination)

| Source in this repo | Global destination (per-user, no sudo) | Project destination (per-repo, committed) |
|---|---|---|
| `agents/*.md` (7 files) | `~/.config/opencode/agents/*.md` | `<project>/.opencode/agents/*.md` |
| `AGENTS.md` (constitution) | `~/.config/opencode/AGENTS.md` | `<project>/AGENTS.md` (rule paths rewritten to `.opencode/rules/`) |
| `rules/*.md` (protocols + security) | `~/.config/opencode/rules/*.md` | `<project>/.opencode/rules/*.md` — **not auto-discovered in V2**; loaded via `instructions` in the config |
| `commands/*.md` | `~/.config/opencode/commands/*.md` | `<project>/.opencode/commands/*.md` |
| `plugins/*` (redact, instructions, guard-audit) | `~/.config/opencode/plugins/*` | `<project>/.opencode/plugins/*` (auto-loaded) |
| `templates/opencode-{global,project}.json` | merged into `~/.config/opencode/opencode.json(c)` | merged into `<project>/opencode.json` |

Resulting global layout (all inside your home, no root):

```
~/.config/opencode/          ← per-user config root (no sudo)
├── AGENTS.md                ← global constitution (merged with <project>/AGENTS.md at runtime)
├── agents/                  ← project-manager.md (primary) + 6 subagents
├── rules/
│   ├── workflow-protocols.md  ← single source of truth (read on demand, not in instructions)
│   └── security-policy.md     ← always loaded via "instructions"
├── commands/                ← /build, /plan slash commands
├── plugins/                 ← redact, instructions, guard-audit
└── opencode.json(c)         ← merged V2 config: default_agent, permissions, experimental, mcp, plugins
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
> To uninstall: re-run `./install.sh` is idempotent; to remove, delete the installed `agents/`, `rules/`, `commands/`, `plugins/` dirs and the harness keys from `opencode.json(c)` (restore from `~/.config/opencode_backups/` if needed).

**What OpenCode V2 discovers (both scopes):**

* **Agents:** `<project>/.opencode/agents/<name>.md` and `~/.config/opencode/agents/<name>.md` → agent ID `<name>` (e.g. `team/reviewer.md` → `team/reviewer`). Frontmatter `mode`, `model`, `permissions`, `steps`, `color`, `hidden`; the Markdown body becomes the `system` prompt. V1 keys (`temperature`, `permission`, `tools`, `disable`, `maxSteps`) are deprecated and rejected by `scripts/validate_opencode_harness.py`.
* **Instructions:** `AGENTS.md` files are auto-discovered; `rules/` is **not** — list rule files in the config `instructions` array (the installer does this for `security-policy.md`).
* **Commands:** `.opencode/commands/*.md` and `~/.config/opencode/commands/*.md` → slash commands (`/build`, `/plan`).
* **Plugins:** `.opencode/plugins/*` auto-load; global plugins are listed in the global config `plugins` array.

Verify discovery: `opencode debug agents` (lists all agents with resolved permissions) and `opencode debug config` (lists merged config sources). Inside the TUI, `/agents` shows `project-manager` (primary) + the subagents.

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
opencode run --agent project-manager "fix the typo in src/main.py"
# → PM detects ≤3 files, asks via question tool: "Direct mode?" → Yes → Developer direct + DevOps commit

# Tier 1 Small — no PLANNING overhead
"Build a Go CLI that converts CSV to JSON (3 files)"
# → PRD + specs/<csv>.md → tests stub → Developer (1 group) → docs specs sync (if changed) → DevOps

# Tier 2 — feature on existing project
"Add OAuth2 token refresh to my existing API (in my project)"
# → glob src/**/*, project_* entity → Architect specs/<oauth-refresh>.md → tests → Developer respects patterns → Test regression → CR → Docs → DevOps feature/<oauth-refresh>

# Tier 3 — bug
"Fix the token refresh race #142"
# → ticket_142_* → Developer root_cause_142_* (file:line + hypothesis) → bug-repro test (FAIL→PASS) → minimal fix → Test regression → CR quick → DevOps fix(auth): ... #142

# Tier 4 — research spike
"Spike: evaluate WebSockets vs SSE for real-time notifications"
# → PM detects spike → creates research brief → Architect researches (50 steps, websearch + context7)
# → Developer implements POC on spike/websockets-vs-sse branch → Documentation consolidates Spike Report
# → PM asks: "Escalate to feature?" → If yes → Tier 1/2 with Spike Report as context
```

### Key files (where to look when debugging)

* `AGENTS.md` — Global coding preferences, language guard, security policy, tier detection, feedback loops (source for PM).
* `rules/workflow-protocols.md` — **Single source of truth** for `TDD Protocol`, `File Integrity Checkpoints`, `Parallelization Protocol`, `Rollback Protocol (stash+branch pre-<scope>)`, `Memory MCP Protocol`, `Document Ownership Map`. Do not duplicate.
* `rules/security-policy.md` — Blocked files/env/commands/secret patterns (mandatory).
* `agents/*.md` — Per-agent system prompts, tier awareness, `tool preference` (native `glob/read/grep` primary), `steps`, `model`, `permissions`.
* `docs/` — Generated at runtime: `PRD.md`, `specs/*.md` (AC-N G/W/T), `PLANNING.md`, `IMPLEMENTATION_ROADMAP.md` (with `Parallel group: A/B` + `status`), `PROJECT_CONTEXT.md` (living state), `CHANGELOG.md` (derived), `README.md`, `API_REFERENCE.md`, `spikes/*.md` (Spike Reports from Tier 4).
* `commands/build.md` + `plan.md` — `/build` and `/plan` slash commands for the built-in `build` (full-access) / `plan` (restricted) agents.

## Project Structure

```
minionhorde/                 ← source repo (what you clone)
├── AGENTS.md                ← source constitution → ~/.config/opencode/AGENTS.md or <project>/AGENTS.md
├── agents/                  ← source agents → ~/.config/opencode/agents/ or <project>/.opencode/agents/
│   ├── project-manager.md   ← primary (default_agent)
│   ├── architect.md
│   ├── developer.md
│   ├── test.md
│   ├── code-review.md
│   ├── devops.md
│   └── documentation.md
├── rules/                   ← source rules → ~/.config/opencode/rules/ or <project>/.opencode/rules/
│   ├── workflow-protocols.md  ← single source of truth (read on demand)
│   └── security-policy.md     ← always loaded via config "instructions"
├── commands/                ← /build, /plan → ~/.config/opencode/commands/ or <project>/.opencode/commands/
├── plugins/                 ← V2 plugins → ~/.config/opencode/plugins/ or <project>/.opencode/plugins/
│   ├── redact/              ← secret scrubbing (prompts, requests, tool input)
│   ├── instructions/        ← shrinks the <env> system block to Platform only
│   └── guard-audit/         ← dangerous-shell deny (ask→deny escalation) + hash-chained audit log (.opencode/audit/guard-audit.jsonl)
├── templates/
│   ├── opencode-global.json   ← merged into ~/.config/opencode/opencode.json(c)
│   └── opencode-project.json  ← merged into <project>/opencode.json
├── scripts/                 ← merge_opencode_config.py, validate_opencode_harness.py, ...
├── install.sh               ← installer (global | project <path> | both <path>)
├── LICENSE
└── README.md
```

When installed, OpenCode resolves:
* **Global:** `~/.config/opencode/AGENTS.md` + `~/.config/opencode/agents/*.md` + `~/.config/opencode/commands/*.md` + `~/.config/opencode/plugins/*` + merged `opencode.json(c)` (per-user, no sudo)
* **Project:** `<project>/AGENTS.md` + `<project>/.opencode/{agents,commands,plugins,rules}/*` + `<project>/opencode.json` (project wins on conflict)

## Protocols (deep dive)

* **Delegation Prompt Template (mandatory):** Every `subagent` call pastes `rules/workflow-protocols.md §…` excerpt + `Required Skills — On Demand` (e.g. `python-enterprise` only for Python stack) + `specs` content + `Verify BEFORE/AFTER globs` + `Output Contract`. Agent system prompts are loaded automatically by OpenCode — do NOT paste `agents/<agent>.md` (redundant, wastes ~4.5k tokens).
* **Tool preference:** Native `read`/`glob`/`grep` for gates, `filesystem` MCP only for `directory_tree`/`allowed_directories`. Batch independent `glob`s in parallel, use `docs/specs/*.md` not `**/*`, cache per phase.
* **Memory MCP:** `project_*`, `workflow_*`, `ticket_*`, `decision_*`, `implementation_*`, `root_cause_*`, `incident_*`, `audit_*` — see `rules/... §Memory MCP Protocol` for creation/ownership/timing. Never `read_graph`.
* **Tier 4 Spike Workflow:** Structured research pipeline. PM detects spike → creates brief → Architect researches (50 steps, `websearch` reinforced) → Developer implements POC (no TDD) → Documentation consolidates Spike Report → PM offers escalation to Tier 1/2. See `rules/workflow-protocols.md §Tier 4: Research / Spike Workflow`.

## Troubleshooting

* **Agent not visible in `/agents`:** Check `agents/<name>.md` frontmatter `mode: primary|subagent|all`, `hidden: false`. Path `<project>/.opencode/agents/team/reviewer.md` → ID `team/reviewer`; global `~/.config/opencode/agents/reviewer.md` → ID `reviewer`.
* **`command not found: opencode`:** Fallback path `~/.opencode/bin` not in `PATH`. Add `export PATH="$HOME/.opencode/bin:$PATH"` or use `OPENCODE_INSTALL_DIR=$HOME/.local/bin`.
* **Subagent cannot edit:** Check `permissions` has `edit: allow` + `subagent: { "<agent-id>": allow }` in the parent. Last matching rule wins — put `deny *` before `allow <id>`. Nested delegation needs `experimental.subagent_depth: 2` (set by the installer).
* **Tests not created before code:** TDD gate failed — verify `glob tests/<slug>.*` exists before Developer. See `§TDD Protocol Violations`.
* **Rollback fails to find branch:** Check unified naming `backup/pre-<scope>-<timestamp>` where `<scope>` = `phase-<N>` or `group-<letter>` (see `§Rollback §Naming Convention`).

## Contributing

PRs welcome. Keep tier-aware pruning: don't add artefacts for Tier 0/Small, keep `rules/workflow-protocols.md` as single source of truth, respect `security-policy.md` (never read `.env`, tokens, keys).

## License

MIT — see `LICENSE`.

---

*Built for OpenCode V2. Tested with OpenCode v2.3.2 (TUI + `opencode debug agents`/`debug config`). For OpenCode docs: `opencode.ai/docs`, `opencode.ai/docs/agents`, `opencode.ai/docs/permissions`, `opencode.ai/docs/config`, `opencode.ai/docs/build/plugins`.*
