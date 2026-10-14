// Instructions plugin — two jobs on the system prompt, in this order:
//
//  1. SCRUB — replaces OpenCode's `<env>` block with a controlled one that
//     carries only `Platform`. Removes the working directory, workspace root
//     and git-detection signals that would otherwise be sent to the model
//     provider on every request with no opt-in and no way to notice.
//
//  2. REACTIVATE — OpenCode V2 accepts the config `instructions` array but does
//     not load it (documented: "OpenCode accepts this field but does not load
//     its entries; use AGENTS.md for instructions"). This plugin reads that
//     array and injects any file OpenCode has not already injected, so the
//     field keeps working as the single source of truth.
//
// The scrub runs first on purpose: it is the security-critical half, and doing
// it before any injection means a failure downstream cannot reopen the leak.
//
// No logging. `console.log` from a plugin does not reach opencode.log — the
// file holds nothing but structured lines — so printing would be dead code.
// Verification is functional, see README.md.

import { readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import { Plugin } from "@opencode/plugin"
import { markerOf, scrubEnv } from "./instructions.ts"

const CONFIG_DIR = process.env.XDG_CONFIG_HOME
  ? join(process.env.XDG_CONFIG_HOME, "opencode")
  : join(homedir(), ".config", "opencode")

/** The only part of a system prompt this plugin reads or writes. */
interface SystemTextPart {
  readonly type: "text"
  readonly text: string
}

interface SystemPromptEvent {
  system: SystemTextPart[]
}

interface InstructionFile {
  readonly path: string
  readonly content: string
}

const stripLineComments = (json: string) => json.replace(/^\s*\/\/.*$/gm, "")

const expandHome = (path: string) => path.replace(/^~(?=\/)/, homedir())

/**
 * Reads the `instructions` array from the global `opencode.jsonc` and loads
 * each file it names. Runs once at setup, never per request.
 *
 * Line comments are stripped so the JSONC config parses as JSON. This only
 * handles full-line `//` comments; an inline `//` inside a string would break
 * the parse, and the plugin fails to load rather than misbehave silently.
 *
 * @returns One entry per configured instruction file, in declaration order.
 * @throws If the config is unparseable or a named file is missing. The plugin
 *   does not load at all in that case — the scrub does not apply silently.
 */
function loadInstructionFiles(): InstructionFile[] {
  const config = JSON.parse(
    stripLineComments(readFileSync(join(CONFIG_DIR, "opencode.jsonc"), "utf8")),
  ) as { instructions?: string[] }

  return (config.instructions ?? []).map((path) => ({
    path,
    content: readFileSync(expandHome(path), "utf8"),
  }))
}

export default Plugin.define({
  id: "instructions",
  async setup(ctx) {
    const files = loadInstructionFiles()

    const apply = (event: SystemPromptEvent) => {
      for (const [index, part] of event.system.entries()) {
        if (!part.text.includes("<env>")) continue
        event.system[index] = { ...part, text: scrubEnv(part.text, process.platform) }
      }

      for (const file of files) {
        const marker = markerOf(file.content)
        if (event.system.some((part) => part.text.includes(marker))) continue
        event.system.push({ type: "text", text: file.content })
      }
    }

    for (const kind of ["context", "compaction", "generate", "title"] as const) {
      await ctx.session.hook(kind, apply)
    }
  },
})
