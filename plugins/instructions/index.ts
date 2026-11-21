// Instructions plugin — two jobs on the system prompt, in this order:
//
//  1. SCRUB — replaces OpenCode's `<env>` block with a controlled one that
//     carries only `Platform`. Removes the working directory, workspace root
//     and git-detection signals that would otherwise be sent to the model
//     provider on every request with no opt-in and no way to notice.
//
// OpenCode V2 loads the `instructions` array natively, so this plugin only
// scrubs OpenCode's `<env>` block to a controlled allowlist carrying
// `Platform`. The previous "REACTIVATE" half that re-injected instruction
// files was removed: it read the user's global config and duplicated native
// V2 loading.
//
// No logging. `console.log` from a plugin does not reach opencode.log — the
// file holds nothing but structured lines — so printing would be dead code.
// Verification is functional, see README.md.

import { Plugin } from "@opencode/plugin"
import { scrubEnv } from "./instructions.ts"

/** The only part of a system prompt this plugin reads or writes. */
interface SystemTextPart {
  readonly type: "text"
  readonly text: string
}

interface SystemPromptEvent {
  system: SystemTextPart[]
}

export default Plugin.define({
  id: "instructions",
  async setup(ctx) {
    const apply = (event: SystemPromptEvent) => {
      for (const [index, part] of event.system.entries()) {
        if (!part.text.includes("<env>")) continue
        event.system[index] = { ...part, text: scrubEnv(part.text, process.platform) }
      }
    }

    for (const kind of ["context", "compaction", "generate", "title"] as const) {
      await ctx.session.hook(kind, apply)
    }
  },
})
