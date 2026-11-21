import { appendFileSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync } from "node:fs"
import { createHash } from "node:crypto"
import { dirname } from "node:path"

export type AuditEntryStatus = "success" | "error" | "interrupted" | "denied"

export interface AuditEntry {
  schema_version: "audit-v2-oc"
  timestamp: string
  event: string
  tool: string
  target: string
  status: AuditEntryStatus
  classification: string
  prev_hash: string
  hash: string
}

const SCHEMA = "audit-v2-oc"
const MAX_BYTES = 1_000_000
const MAX_ROTATED = 3

function canonicalValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalValue)
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, canonicalValue(item)]))
  }
  return value
}

function canonical(entry: Omit<AuditEntry, "hash">): string {
  return JSON.stringify(canonicalValue(entry))
}

function hashOf(entry: Omit<AuditEntry, "hash">): string {
  return createHash("sha256").update(canonical(entry)).digest("hex")
}

function lastHash(path: string): string {
  try {
    const lines = readFileSync(path, "utf8").split("\n")
    for (let index = lines.length - 1; index >= 0; index -= 1) {
      if (!lines[index].trim()) continue
      try {
        const parsed = JSON.parse(lines[index]) as { hash?: string }
        if (typeof parsed.hash === "string" && parsed.hash) return parsed.hash
      } catch { /* scan earlier entries */ }
    }
  } catch { /* missing log */ }
  return ""
}

function rotate(path: string): void {
  try {
    if (statSync(path).size < MAX_BYTES) return
  } catch { return }
  for (let index = MAX_ROTATED; index >= 1; index -= 1) {
    const source = `${path}.${index}`
    const target = `${path}.${index + 1}`
    try { rmSync(target) } catch { /* absent */ }
    try { renameSync(source, target) } catch { /* absent */ }
  }
  renameSync(path, `${path}.1`)
}

export function appendAudit(input: {
  tool: string
  target: string
  event: string
  status: AuditEntryStatus
  classification: string
  logPath: string
}): AuditEntry {
  mkdirSync(dirname(input.logPath), { recursive: true })
  rotate(input.logPath)
  const safeTarget = scrubSecret(input.target)
  const body = {
    schema_version: SCHEMA,
    timestamp: new Date().toISOString(),
    event: input.event,
    tool: input.tool,
    target: safeTarget,
    status: input.status,
    classification: input.classification,
    prev_hash: lastHash(input.logPath),
  }
  const entry: AuditEntry = { ...body, hash: hashOf(body) }
  appendFileSync(input.logPath, JSON.stringify(entry) + "\n")
  return entry
}

export function verifyAudit(path: string): { ok: boolean; errors: string[] } {
  let previous = ""
  const errors: string[] = []
  try {
    const lines = readFileSync(path, "utf8").split("\n")
    lines.forEach((line, index) => {
      if (!line.trim()) return
      let parsed: Record<string, unknown>
      try { parsed = JSON.parse(line) as Record<string, unknown> }
      catch { errors.push(`line ${index + 1}: invalid JSON`); return }
      const { hash, ...body } = parsed
      const expected = hashOf(body as Omit<AuditEntry, "hash">)
      if (hash !== expected) errors.push(`line ${index + 1}: hash mismatch`)
      if (body.prev_hash !== previous) errors.push(`line ${index + 1}: broken chain`)
      previous = typeof hash === "string" ? hash : ""
    })
  } catch { errors.push("missing audit log") }
  return { ok: errors.length === 0, errors }
}

export function scrubSecret(target: string): string {
  return target
    .replace(/(password|token|secret|api[_-]?key|auth)=([^&\s]+)/gi, "$1=[REDACTED]")
    .replace(/[A-Za-z0-9]{20,}/g, "[REDACTED:secret]")
}

export function listRotations(path: string): string[] {
  try {
    return readdirSync(dirname(path))
      .filter((name) => name.startsWith(`${path.split("/").pop()}.`))
      .sort()
  } catch { return [] }
}
