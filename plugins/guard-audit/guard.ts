export type GuardEffect = "allow" | "ask" | "deny"

export interface GuardDecision {
  effect: GuardEffect
  reason: string
  classification: string
}

const denyPatterns: Array<[RegExp, string, string]> = [
  [/\bgit\s+(?:push\s+.*(?:--force(?:-with-lease)?|--mirror)|reset\s+--hard|clean\s+.*(?:-f|--force)|stash\s+(?:drop|clear))/i, "irreversible_git", "irreversible git operation"],
  [/(?:^|[;&|])\s*rm\s+(?:(?:-[^-\s]*[rf]|--recursive|--force)[^;|&]*|[^;|&]*\s(?:-[^-\s]*[rf]|--recursive|--force))/i, "destructive_filesystem", "recursive or forced deletion"],
  [/(?:find\s+[^;|&]*\s(?:-delete|-exec(?:dir)?\s+(?:rm|shred|unlink)))/i, "destructive_find", "destructive find operation"],
  [/(?:\b(?:drop\s+(?:table|database)|delete\s+from|truncate\s+(?:table)?))/i, "destructive_sql", "destructive SQL operation"],
  [/(?:\bsudo\b|\bchmod\s+(?:0?777|a\+rwx)|--privileged\b|0\.0\.0\.0)/i, "privilege_or_exposure", "privilege or exposure weakening"],
  [/(?:\b(?:curl|wget)\b[^;|&]*(?:https?:\/\/)[^;|&]*\|\s*(?:bash|sh|zsh|python|python3|node|ruby)\b)/i, "remote_code_pipeline", "remote content piped to interpreter"],
  [/(?:node_tls_reject_unauthorized\s*=\s*0|verify\s*=\s*false|pythonhttpsverify\s*=\s*0)/i, "tls_weakening", "TLS verification disabled"],
  [/(?:\b(?:python|python3)\s+-c\s+[^;|&]*(?:shutil\.rmtree|os\.(?:remove|unlink|system)|subprocess\.|rm\s+-rf)|\bnode\s+(?:-e|--eval)\s+[^;|&]*(?:fs\.(?:rm|unlink)|child_process|exec\())/i, "destructive_interpreter", "destructive interpreter code"],
]

const askPatterns: Array<[RegExp, string, string]> = [
  [/\b(?:git\s+push|curl|wget|ssh|scp)\b/i, "network_or_egress", "network or external side effect"],
  [/\b(?:docker|kubectl|terraform|helm)\b/i, "infrastructure", "infrastructure side effect"],
]

export function classifyShell(command: string): GuardDecision {
  if (!command.trim()) return { effect: "allow", reason: "empty command", classification: "empty" }
  for (const [pattern, classification, reason] of denyPatterns) {
    if (pattern.test(command)) return { effect: "deny", reason, classification }
  }
  for (const [pattern, classification, reason] of askPatterns) {
    if (pattern.test(command)) return { effect: "ask", reason, classification }
  }
  return { effect: "allow", reason: "no high-confidence risk detected", classification: "safe" }
}

export function preserveExplicitDeny(effect: string, decision: GuardDecision): GuardDecision {
  return effect === "deny" ? { effect: "deny", reason: "explicit permission deny", classification: "explicit_deny" } : decision
}
