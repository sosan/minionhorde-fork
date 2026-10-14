// Redact plugin — scrubs secrets from everything that leaves the session:
//  1. Outbound LLM requests (context, compaction, generate, title).
//  2. Incoming user prompts (before they are admitted/persisted).
//  3. Tool inputs before execution (only listed tools, or all with strictTools).
// Values are replaced with stable [REDACTED_<n>] tokens; the originals are
// never logged and are intentionally not restored.

import { Plugin } from "@opencode/plugin"
import { collectSecrets, makeRedactor, type RedactOptions } from "./redact"

export default Plugin.define({
  id: "redact",
  async setup(ctx) {
    const options = (ctx.options ?? {}) as RedactOptions
    const set = collectSecrets(process.env, options)
    const r = makeRedactor(set)

    console.log(
      `[redact] loaded: ${set.count} literal secrets, ${set.patterns.length} patterns ` +
        `(strictTools=${options.strictTools === true}, redactShell=${options.redactShell === true})`,
    )

    // Redact the assembled request right before it is dispatched to the model.
    const redactRequest = (event: { system?: unknown; messages?: unknown }) => {
      if (Array.isArray(event.system)) r.value(event.system)
      if (Array.isArray(event.messages)) r.value(event.messages)
    }
    for (const kind of ["context", "compaction", "generate", "title"] as const) {
      await ctx.session.hook(kind, redactRequest)
    }

    // Redact the user prompt before admission so it is never persisted or sent.
    if (options.redactPrompt !== false) {
      await ctx.session.hook("prompt", (event) => {
        event.prompt.text = r.text(event.prompt.text)
      })
    }

    const toolList = new Set(options.redactTools ?? [])
    const shouldRedactTool = (id: string) => options.strictTools === true || toolList.has(id)

    // Redact tool arguments before the tool runs (network-facing tools by
    // default; every tool with strictTools).
    await ctx.tool.hook("execute.before", (event) => {
      if (shouldRedactTool(event.tool)) r.value(event.input)
    })

    // Opt-in: redact shell command text. Disabled by default because it can
    // break legitimate local commands that legitimately contain token-like text.
    if (options.redactShell === true) {
      await ctx.shell.hook("create.before", (event) => {
        event.command = r.text(event.command)
      })
    }
  },
})