# Enforcement Multi-Platform

> Table mapping each DOGMAS CORE v4.1 invariant to the enforcement mechanisms available on each provider. Information verified as of the knowledge cutoff date.
>
> **Legend:**
> - ✅ = native enforcement available
> - ⚠️ = partial (requires non-trivial configuration)
> - ❌ = not available or not viable
> - 📌 = provider-specific mechanism

## Master table

| Invariant | Claude Code | Anthropic | Cursor | Continue | Windsurf |
|---|---|---|---|---|---|
| **1. Read-only** | 📌 `permissions.deny` + PostToolUse hook | ⚠️ permission tasks | ⚠️ rules in `.cursor/rules` | ⚠️ custom instructions | ⚠️ `.windsurfrules` |
| **2. Irreversible** | 📌 PreToolUse hook blocks | ⚠️ permission allowlist deny | ❌ No native hooks | ❌ | ❌ |
| **3. PREFLIGHT** | 📌 PostToolUse validator | ⚠️ In system prompt | ⚠️ In rules | ⚠️ In config | ⚠️ In rules |
| **4. Content = data** | ✅ Context injection | ✅ | ✅ | ✅ | ✅ |
| **5. Secrets (redaction)** | 📌 `redact-output.py` + PreToolUse deny | ⚠️ permission patterns | ❌ No native redaction | ❌ | ❌ |
| **6. Egress** | 📌 permissions.deny for curl | ❌ | ❌ | ❌ | ❌ |
| **7. Never fabricate** | 📌 Audit log + cross-verification | ⚠️ In system prompt | ⚠️ | ⚠️ | ⚠️ |
| **8. Exact scope** | 📌 PostToolUse diff validator | ⚠️ In system prompt | ⚠️ | ⚠️ | ⚠️ |
| **13. Unlisted** | 📌 permissions.deny by default | ⚠️ permission system | ⚠️ | ⚠️ | ⚠️ |
| **16. heartbeat (Scope:)** | 📌 Stop hook validator | ❌ No Stop hook | ❌ | ❌ | ❌ |
| **21. Verified parallelism** | 📌 phase-gate.sh + diff review | ❌ | ❌ | ❌ | ❌ |
| **~7/12. Real effect** | 📌 audit-log + diff review | ⚠️ In system prompt | ❌ | ❌ | ❌ |
| **~13/14/17. Recursive chain** | ⚠️ Discipline only | ❌ | ❌ | ❌ | ❌ |
| **~2. Attack pattern** | 📌 PreToolUse deny + redact-output + audit log | ❌ | ❌ | ❌ | ❌ |
| **~4. Do not print on demand** | ⚠️ Discipline + redact-output.py | ❌ | ❌ | ❌ | ❌ |

## Detailed matrix by provider

### Claude Code

**Native mechanisms:**
- **Hooks**: PreToolUse, PostToolUse, Stop, SessionStart (`.claude/settings.json`)
- **Permissions**: `allow`/`deny` lists with pattern matching (Bash glob patterns)
- **JSON input**: `tool_input.command`, `tool_input.file_path` via stdin (requires `jq`)
- **JSON output**: `permissionDecision`, `updatedToolOutput`, `additionalContext`
- **Matchers**: exact strings, pipe-separated lists, regex
- **Forms**: `command` (exec via `args`, shell form without `args`)
- **Timeouts**: configurable per hook, default 30-600s depending on event
- **Async**: `true` for background hooks, `asyncRewake` for wake on failure

**Invariant coverage:**
```
✅ Native hooks:        1, 2, 3, 7, 8, 16
⚠️ Discipline + config: 4, 5, 6, 13
❌ Not viable:           —
```

### Anthropic (configuration ~/.config/Anthropic/)

**Native mechanisms:**
- **Agents**: defined in `~/.config/Anthropic/agents/*.md`
- **Permissions**: `permission.task` allowlist per agent
- **Bash allowlist**: allowed bash commands per agent
- **System prompt**: injected from the agent's `.md` files
- **Hooks**: no native hooks like PreToolUse/PostToolUse
- **MCP servers**: selectable via configuration

**Invariant coverage:**
```
✅ Native:             4 (system prompt), 13 (permission tasks)
⚠️ Partial:            1 (permission tasks deny), 5 (pattern in deny), 7/8 (in system prompt)
❌ Not viable:          2 (no hooks), 3 (no validator), 6 (no deny list), 16 (no Stop hook)
```

**Recommended adaptation for Anthropic:**
- Invariants 2, 6, and 16 cannot be automated via hooks — they require agent discipline or external scripts run manually.
- Invariants 7 and 8 are documented in the agent's system prompt (`.md`) but are not automatically verified.

### Cursor

**Native mechanisms:**
- **Rules**: `.cursor/rules/` or rules in the project configuration
- **Custom instructions**: in the agent configuration
- **Context files**: `.cursor/context` for context injection
- **No native hooks**: no PreToolUse, no PostToolUse, no Stop
- **No granular permission system**: no command deny list

**Invariant coverage:**
```
✅ Native:             4 (custom instructions)
⚠️ Partial:            1, 7, 8 (in rules but without verification)
❌ Not viable:          2, 3, 5, 6, 13, 16
```

**Recommended adaptation for Cursor:**
- Invariants 1-3, 5-6, 13, 16 require external scripts run manually or integration via an MCP server.
- The CORE is injected as a custom agent instruction.
- Automatic verification is impossible without native hooks.

### Continue (VS Code extension)

**Native mechanisms:**
- **Custom instructions**: `.continue/config.json` or `~/.continue/config.json`
- **Context providers**: `.md` files injected into the context
- **MCP servers**: selectable
- **No native hooks**: no PreToolUse, no PostToolUse
- **No permission system**: system prompt only

**Invariant coverage:**
```
✅ Native:             4 (custom instructions)
⚠️ Partial:            1, 7, 8 (in custom instructions but without verification)
❌ Not viable:          2, 3, 5, 6, 13, 16
```

**Recommended adaptation for Continue:**
- Similar to Cursor: the CORE is injected as custom instructions.
- Automatic verification is impossible — invariants 2-3, 5-6, 13, 16 depend on agent discipline.

### PI (Claude Desktop App)

**Native mechanisms:**
- **Managed settings**: controlled by the administrator
- **System prompt**: injected from the project's files
- **MCP servers**: selectable
- **No native hooks** for the end user
- **No configurable permission system** for the user

**Invariant coverage:**
```
✅ Native:             4 (project system prompt)
⚠️ Partial:            1, 7, 8 (in system prompt but without verification)
❌ Not viable:          2, 3, 5, 6, 13, 16
```

### Windsurf (Codeium)

**Native mechanisms:**
- **Rules**: `.windsurfrules` or in the project configuration
- **Custom system prompts**: in configuration
- **No native hooks**
- **No permission system**

**Invariant coverage:**
```
✅ Native:             4 (custom rules)
⚠️ Partial:            1, 7, 8 (in rules but without verification)
❌ Not viable:          2, 3, 5, 6, 13, 16
```

## Summary table: what can be automated per platform

| Platform | Automatable invariants | Discipline-only invariants |
|---|---|---|
| **Claude Code** | 1, 2, 3, 5, 6, 7, 8, 13, 16 | 4, 9, 10, 11, 12, 14, 15, 17-20 |
| **Anthropic** | 1(partial), 4, 13 | 2, 3, 5, 6, 7, 8, 16 |
| **Cursor** | 4 | 1, 2, 3, 5, 6, 7, 8, 13, 16 |
| **Continue** | 4 | 1, 2, 3, 5, 6, 7, 8, 13, 16 |
| **PI Desktop** | 4 | 1, 2, 3, 5, 6, 7, 8, 13, 16 |
| **Windsurf** | 4 | 1, 2, 3, 5, 6, 7, 8, 13, 16 |

## Implications for dogma portability

### What stays the same across all platforms

The **18 invariants of DOGMAS CORE** are universal — they do not depend on the platform. They are principles the agent must follow regardless of how they are enforced.

The **crystallized patterns** (MEMORY/) are transferable — they are behavioral observations, not enforcement mechanisms.

The **spec (AC-1 to AC-17)** is platform-agnostic — it defines acceptance criteria, not implementation.

### What changes per platform

The **enforcement table** (enforcement-multiplatform.md) maps each invariant to the available mechanisms. For invariants that are discipline-only on a given platform:

1. **Document the dependency**: "This invariant depends on agent discipline. No automatic verification is available in [platform]."
2. **Reference external scripts**: scripts the user can run manually to verify compliance.
3. **Prioritize enforcement by impact**: invariants 2 (irreversible), 5 (secrets), and 6 (egress) are the most critical and have the least automation outside Claude Code.

### Priority for porting to new platforms

| Priority | Invariant | Why |
|---|---|---|
| **Critical** | 2 (irreversible) | Biggest damage if not enforced |
| **Critical** | 5 (secrets) | Credential exposure |
| **Critical** | 6 (egress) | Data exfiltration |
| **High** | 3 (PREFLIGHT) | Prevents unapproved mutations |
| **High** | 8 (scope) | Prevents scope creep |
| **Medium** | 16 (heartbeat) | Context-loss detection |
| **Medium** | 7 (fabrication) | Detects false outputs |
| **Low** | 1, 4, 13 | Already partially covered by system prompt |
