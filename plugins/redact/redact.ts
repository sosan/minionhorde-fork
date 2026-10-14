// Redaction engine for the "redact" OpenCode plugin.
// Collects secret values from the environment and explicit options, then
// replaces them (and known secret patterns) with stable [REDACTED_<n>] tokens.
// This module is pure (no OpenCode imports) so it can be unit-tested with node.

export interface RedactOptions {
  /** Redact incoming user prompts before they are admitted. Default: true. */
  redactPrompt?: boolean
  /** Tool IDs whose input is redacted before execution. Default: none. */
  redactTools?: string[]
  /** Redact the input of every tool before execution. Default: false. */
  strictTools?: boolean
  /** Redact shell command text before execution. Default: false. */
  redactShell?: boolean
  /** Exact secret values to redact in addition to those from the environment. */
  secrets?: string[]
  /** Extra regex sources for secret detection. Inline flags are not supported. */
  patterns?: string[]
  /** Minimum length for values collected from the environment. Default: 4. */
  minSecretLength?: number
}

interface Pattern {
  re: RegExp
  /** Custom replacement; receives the full match. Defaults to a stable token. */
  replace?: (match: string) => string
}

export interface SecretSet {
  /** Combined literal secret regex (sorted longest-first), or null when empty. */
  literal: RegExp | null
  patterns: Pattern[]
  count: number
}

export interface Redactor {
  text(input: string): string
  value(input: unknown): unknown
}

const SENSITIVE_NAME =
  /(?:API[_-]?KEY|ACCESS[_-]?KEY|PRIVATE[_-]?KEY|ENCRYPTION[_-]?KEY|SIGNING[_-]?KEY|DEPLOY[_-]?KEY|CLIENT[_-]?SECRET|CREDENTIALS?|TOKEN|SECRET|PASSWORD|PASSWD|AUTH[_-]?(?:TOKEN|KEY|PASSWORD|CREDENTIALS?)|SESSION[_-](?:TOKEN|KEY|SECRET)|DATABASE_URL|DB_URL|MONGODB_URI|REDIS_URL|POSTGRES_URL|PGPASSWORD|BEARER)/i

const DB_URL_RE = /((?:postgres|mysql|mongodb|redis|amqp|rabbit|mssql):\/\/)[^:\s]+:[^@\s]+@/gi

const DEFAULT_PATTERNS: Pattern[] = [
  { re: /(?:ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{36}/g },
  { re: /github_pat_[0-9A-Za-z]{36,}/g },
  { re: /sk-[A-Za-z0-9_-]{32,}/g },
  { re: /api-[A-Za-z0-9_-]{32,}/g },
  { re: /xox[baprs]-[A-Za-z0-9]{10,}/g },
  { re: /AKIA[0-9A-Z]{16}/g },
  { re: /aws_secret_access_key\s*=\s*['"][A-Za-z0-9/+=]{40}['"]/gi },
  { re: /aws_access_key_id\s*=\s*['"][A-Za-z0-9]{20}['"]/gi },
  { re: /-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----/g },
  { re: /-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/g },
  { re: /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g },
  {
    re: /Authorization:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{10,}/gi,
    replace: (m) => m.replace(/^(Authorization:[^A-Za-z0-9]*(?:Bearer|Basic)[^A-Za-z0-9]+).*$/i, "$1[REDACTED]"),
  },
  { re: /Bearer\s+[A-Za-z0-9._~+/=-]{20,}/g, replace: () => "Bearer [REDACTED]" },
  { re: DB_URL_RE, replace: (m) => `${m.split("://")[0]}://[REDACTED]@` },
  { re: /(?:key|secret|token|password|passwd|credential|auth|api|jwt)\s*[:=]\s*['"]?[A-Za-z0-9_\-+/=]{16,}['"]?/gi },
]

const EXCLUDED_VALUES = new Set([
  "true", "false", "null", "undefined", "none", "yes", "no", "nan", "infinity", "0", "1",
])

const escapeRegExp = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")

const compilePattern = (source: string): Pattern => {
  const inlineIgnoreCase = source.startsWith("(?i)")
  const body = inlineIgnoreCase ? source.slice(4) : source
  return { re: new RegExp(body, inlineIgnoreCase ? "gi" : "g") }
}

export function collectSecrets(env: Record<string, string | undefined>, options: RedactOptions = {}): SecretSet {
  const values = new Set<string>()
  const min = options.minSecretLength ?? 4

  for (const [name, raw] of Object.entries(env)) {
    if (!raw || !SENSITIVE_NAME.test(name)) continue
    const value = raw.trim()
    if (value.length < min || /^\d+$/.test(value) || EXCLUDED_VALUES.has(value.toLowerCase())) continue
    values.add(value)
  }
  for (const secret of options.secrets ?? []) {
    const value = secret.trim()
    if (value) values.add(value)
  }

  const patterns: Pattern[] = [...DEFAULT_PATTERNS]
  for (const source of options.patterns ?? []) patterns.push(compilePattern(source))

  const ordered = [...values].sort((a, b) => b.length - a.length)
  return {
    literal: ordered.length ? new RegExp(ordered.map(escapeRegExp).join("|"), "g") : null,
    patterns,
    count: ordered.length,
  }
}

export function makeRedactor(set: SecretSet): Redactor {
  const memo = new Map<string, string>()

  const tokenFor = (value: string): string => {
    const existing = memo.get(value)
    if (existing) return existing
    const token = `[REDACTED_${memo.size + 1}]`
    memo.set(value, token)
    return token
  }

  const text = (input: string): string => {
    let out = input
    if (set.literal) out = out.replace(set.literal, (m) => tokenFor(m))
    for (const pattern of set.patterns) {
      out = out.replace(pattern.re, (m) => (pattern.replace ? pattern.replace(m) : tokenFor(m)))
    }
    return out
  }

  // Mutates arrays/objects in place (they are owned drafts in hooks) by
  // reassigning redacted string values; returns the same reference.
  const value = (input: unknown, keySensitive = false): unknown => {
    if (typeof input === "string") return keySensitive ? tokenFor(input) : text(input)
    if (Array.isArray(input)) {
      for (let i = 0; i < input.length; i++) input[i] = value(input[i])
      return input
    }
    if (input !== null && typeof input === "object") {
      const record = input as Record<string, unknown>
      for (const [key, item] of Object.entries(record)) {
        record[key] = value(item, SENSITIVE_NAME.test(key))
      }
      return input
    }
    return input
  }

  return { text, value }
}