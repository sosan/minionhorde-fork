import { Plugin } from "@opencode/plugin"
import { classifyShell, preserveExplicitDeny } from "./guard.ts"
import { appendAudit, scrubSecret } from "./audit.ts"

interface PermissionEvent {
  readonly sessionID: string
  readonly action: string
  readonly resources: readonly string[]
  effect: "allow" | "ask" | "deny"
  message?: string
}

interface ShellEvent {
  command: string
  cwd: string
}

interface ToolBeforeEvent {
  readonly tool: string
  readonly input: unknown
}

interface ToolAfterEvent {
  readonly tool: string
  readonly status?: string
  readonly error?: { message?: string }
  readonly result?: unknown
}

function projectLogPath(ctx: { location: { directory: string } }): string {
  return `${ctx.location.directory}/.opencode/audit/guard-audit.jsonl`
}

function summarize(value: unknown): string {
  if (typeof value === "string") return scrubSecret(value).slice(0, 2000)
  try { return scrubSecret(JSON.stringify(value)).slice(0, 2000) } catch { return "[unserializable]" }
}

export default Plugin.define({
  id: "guard-audit",
  async setup(ctx) {
    const logPath = projectLogPath(ctx)

    await ctx.permission.hook("evaluate", (event: PermissionEvent) => {
      const resource = event.resources.join(" ")
      const decision = event.action === "shell" ? classifyShell(resource) : classifyShell(`${event.action} ${resource}`)
      const finalDecision = preserveExplicitDeny(event.effect, decision)
      if (event.effect !== "deny") event.effect = finalDecision.effect
      event.message = finalDecision.reason
      appendAudit({
        tool: event.action,
        target: summarize(resource),
        event: "permission_evaluated",
        status: finalDecision.effect === "deny" ? "denied" : "success",
        classification: finalDecision.classification,
        logPath,
      })
    })

    await ctx.shell.hook("create.before", (event: ShellEvent) => {
      const decision = classifyShell(event.command)
      if (decision.effect === "deny") throw new Error(decision.reason)
      appendAudit({
        tool: "shell",
        target: summarize(event.command),
        event: "shell_before",
        status: decision.effect === "deny" ? "denied" : "success",
        classification: decision.classification,
        logPath,
      })
    })

    await ctx.tool.hook("execute.before", (event: ToolBeforeEvent) => {
      appendAudit({
        tool: event.tool,
        target: summarize(event.input),
        event: "tool_before",
        status: "success",
        classification: "observed",
        logPath,
      })
    })

    await ctx.tool.hook("execute.after", (event: ToolAfterEvent) => {
      appendAudit({
        tool: event.tool,
        target: summarize(event.error ?? event.result),
        event: "tool_after",
        status: event.status === "error" ? "error" : "success",
        classification: "observed",
        logPath,
      })
    })
  },
})
