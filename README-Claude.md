# minionhorde — Claude Code Edition

> Enterprise multi-agent SDLC workflow for Claude Code. Tier-aware activation with quality gates.

## What is this?

A governed multi-agent pipeline for Claude Code that implements a full SDLC:
PRD → specs → planning → TDD → implementation → tests → review → docs → git.

- **One orchestrator** (`project-manager`) that never writes code — only triages, routes, and checks gates.
- **Six subagents** (`architect`, `developer`, `test`, `code-review`, `devops`, `documentation`) invoked via Agent tool.
- **Four tiers** (`Tier 0 direct`, `Tier 1 new-project`, `Tier 2 feature`, `Tier 3 bugfix`) with size-aware activation.
- **Quality gates**: TDD mandatory (AC→TC, red→green), file integrity checkpoints, rollback protocol.

## Prerequisites

- **Claude Code** (v2.1+)
- **Node.js 18+** (if using MCP servers)
- **Git**
- **Claude API key** or Anthropic subscription

## Installation

```bash
# Clone the repo
git clone https://github.com/ilgrim/minionhorde.git
cd minionhorde

# Install into your project
./install-claude.sh /path/to/your/project

# Or install into current directory
./install-claude.sh .
```

The installer creates a backup of any existing Claude config before overwriting:
- Backup location: `~/.claude_backups/claude_conf_YYYY-MM-DD_HHMMSS.tar.gz`
- Restore: `tar -xzf <file>.tar.gz -C /path/to/project`

## Quick Start

```bash
cd your-project
claude
# Type: "Build me a REST API for task management"
# → PM detects Tier 1 → asks complexity → orchestrates full pipeline
```

## Tiers

| Tier | Trigger | What happens |
|------|---------|--------------|
| **Tier 0** | ≤3 files, trivial, "direct" | PM → Developer → DevOps. No docs, no TDD. |
| **Tier 1** | "build/create/develop" new project | Full pipeline: PRD → specs → TDD → impl → review → docs → git |
| **Tier 2** | "add/feature/extend" existing | Impact analysis → spec → TDD → impl → review → docs → git |
| **Tier 3** | "fix/bug/error" or ticket | Root cause → bug-repro test → minimal fix → validation → git |

### Tier 1 Size

| Size | Files | Agents Activated |
|------|-------|-------------------|
| Small | <5 | PM + Developer + Test |
| Medium | 5-20 | + Architect + Code Review |
| Large | >20 | All agents full |

## Agents

| Agent | Role | Model | Tools |
|-------|------|-------|-------|
| **project-manager** | Orchestrator, tier detection, gates | sonnet-4 | Read, Glob, Grep, Agent, TodoWrite, WebSearch, WebFetch |
| **architect** | Technical planning, PLANNING.md | sonnet-4 | Read, Glob, Grep, WebSearch, WebFetch |
| **developer** | Tier-aware implementation, docstrings | opus-4 | Read, Glob, Grep, Write, Edit, Bash, Agent, TodoWrite |
| **test** | TDD stubs, execution, regression, coverage | opus-4 | Read, Glob, Grep, Write, Bash, TodoWrite |
| **code-review** | Quality + security review, incidents | sonnet-4 | Read, Glob, Grep, TodoWrite |
| **devops** | Git (conventional commits), changelog, CI/CD | opus-4 | Read, Glob, Grep, Write, Edit, Bash, TodoWrite |
| **documentation** | Specs sync, README, API_REFERENCE | sonnet-4 | Read, Glob, Grep, Write, Edit, TodoWrite |

## Workflow Phases

```
Phase 0: Detect & Assess (PM)
    │  Detect tier, ask complexity questions, create feature branch
    ▼
Phase 1: Requirements (PM) [Tier 1 only]
    │  Create docs/PRD.md + docs/specs/<slug>.md
    ▼
Phase 1b: TDD Stubs (Test)
    │  Create tests/<slug>.* with AC→TC mapping (must FAIL)
    ▼
Phase 2: Planning (Architect) [Medium/Large only]
    │  Create docs/PLANNING.md + docs/IMPLEMENTATION_ROADMAP.md
    ▼
Phase 3: Implementation (Developer)
    │  Implement by parallel groups (make tests PASS)
    ▼
Phase 4: Code Review (Code Review)
    │  Quality + security review. Feedback loop if Critical/High/Medium.
    ▼
Phase 5: Documentation (Documentation)
    │  Sync specs (incremental, only if git diff shows change)
    ▼
Phase 6: Git & Changelog (DevOps)
       Commit with conventional message, generate CHANGELOG
```

## TDD Protocol

Mandatory for Tier 1, 2, and 3:

1. PM creates spec with Acceptance Criteria: `AC-N: GIVEN / WHEN / THEN`
2. Test creates test stubs: `1 AC → 1 TC`, tests must **FAIL** (red phase)
3. Developer implements **only** to make tests **PASS** (green phase)
4. Test validates (max 3 iterations, then escalate)
5. PM confirms phase

## Rollback Protocol

Before each implementation phase, two safety nets are created:

```bash
# 1. Stashpoint (fast restore)
git stash push -m "pre-<scope> - <name>" --keep-index --include-untracked

# 2. Backup branch (hard restore)
git branch backup/pre-<scope>-<timestamp>
```

On failure: stash pop first, then backup branch fallback, then escalate.

## File Structure

```
your-project/
├── CLAUDE.md                      # Constitution (always loads)
├── .claude/
│   ├── settings.json              # Permissions + hooks
│   ├── agents/
│   │   ├── project-manager.md
│   │   ├── architect.md
│   │   ├── developer.md
│   │   ├── test.md
│   │   ├── code-review.md
│   │   ├── devops.md
│   │   └── documentation.md
│   ├── rules/
│   │   ├── workflow.md            # TDD, parallelization, rollback
│   │   ├── security.md            # Blocked files/commands
│   │   └── testing.md             # Testing protocol
│   └── skills/
│       └── sdlc-workflow/
│           └── SKILL.md           # Full workflow skill
├── docs/
│   ├── templates/                 # Claude-specific templates
│   │   ├── PRD.md
│   │   ├── SPEC.md
│   │   └── PROJECT_CONTEXT.md
│   ├── PRD.md                     # Generated at runtime
│   ├── specs/                     # Generated at runtime
│   ├── PLANNING.md                # Generated at runtime
│   ├── PROJECT_CONTEXT.md         # Generated at runtime
│   └── CHANGELOG.md               # Generated at runtime
├── src/                           # Your source code
└── tests/                         # Your tests
```

## Configuration

### Permissions (settings.json)

Default allowed tools (no confirmation needed):
- Read, Glob, Grep, WebSearch, WebFetch, TodoWrite

Other tools require confirmation per Claude Code defaults.

### Hooks

PostToolUse hook auto-formats code after Write/Edit:
- Python: `black`
- JavaScript/TypeScript: `prettier`
- Go: `gofmt`

### Skills

The `sdlc-workflow` skill loads on-demand when you invoke it or when Claude detects a workflow-related task.

## Troubleshooting

**Agent not available:** Check `.claude/agents/` directory exists and files have correct frontmatter.

**Permission denied:** Check `settings.json` permissions. Add tools to `allow` list if needed.

**Hooks not running:** Verify `settings.json` hook syntax. Hooks require Claude Code v2.1+.

**Tests not created before code:** TDD gate failed. Verify Test Agent was delegated before Developer.

## Differences from OpenCode Version

| Feature | OpenCode | Claude Code |
|---------|----------|-------------|
| Config location | `~/.config/opencode/` | `.claude/` (project) |
| Agent definition | `agents/*.md` with frontmatter | `.claude/agents/*.md` with frontmatter |
| Orchestration | `task` tool | `Agent` tool |
| State persistence | Memory MCP (knowledge graph) | MEMORY.md + docs/ files |
| Rules | `rules/workflow-protocols.md` (single file) | `.claude/rules/*.md` (scoped) |
| Skills | Loaded on-demand from system | `.claude/skills/` directories |
| Workflows | Dynamic (JavaScript) | Agent tool orchestration |
| Hooks | None | PostToolUse auto-format |

## License

MIT — see [LICENSE](LICENSE).
