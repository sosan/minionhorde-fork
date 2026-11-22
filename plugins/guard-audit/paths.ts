import { basename, join } from "node:path"

/**
 * Resolve the audit log path relative to OpenCode's plugin location.
 *
 * OpenCode sets `ctx.location.directory` to the project's `.opencode`
 * directory when plugins are installed there. Appending another
 * `/.opencode` segment would nest the log as `.opencode/.opencode/audit`.
 * This helper appends `audit/guard-audit.jsonl` directly when the base
 * directory already ends with `.opencode`.
 */
export function resolveAuditPath(baseDir: string): string {
  const normalizedBase = baseDir.replace(/[\\/]+$/, "")
  const auditDir = basename(normalizedBase) === ".opencode"
    ? join(normalizedBase, "audit")
    : join(normalizedBase, ".opencode", "audit")
  return join(auditDir, "guard-audit.jsonl")
}