import assert from "node:assert/strict"
import { test } from "node:test"
import { controlledEnv, markerOf, scrubEnv } from "./instructions.ts"

// Shape produced by `packages/core/src/instructions/builtins.ts` in OpenCode.
const ENV = [
  "<env>",
  "  Working directory: /home/USER/.config/opencode",
  "  Workspace root folder: /home/USER/.config/opencode",
  "  Is directory a git repo: no",
  "  Platform: linux",
  "  Prefer /tmp over generic system temporary directories such as /tmp; it is pre-created and approved for external access.",
  "</env>",
].join("\n")

const BEFORE = ["Here is some useful information about the environment you are running in:", ENV].join("\n")
const CHUNK = ["Today's date: Wed Oct 14 2026", BEFORE, "# Instructions\n"].join("\n\n")

test("controlledEnv emits only Platform", () => {
  assert.equal(controlledEnv("linux"), "<env>\n  Platform: linux\n</env>")
})

test("scrubEnv drops every identifying field and keeps Platform", () => {
  const out = scrubEnv(CHUNK, "linux")
  assert.equal(out.includes("Working directory"), false)
  assert.equal(out.includes("Workspace root folder"), false)
  assert.equal(out.includes("Is directory a git repo"), false)
  assert.equal(out.includes("generic system temporary directories"), false)
  assert.ok(out.includes("Platform: linux"))
})

test("scrubEnv leaves the date, which OpenCode emits outside <env>", () => {
  assert.ok(scrubEnv(CHUNK, "linux").includes("Today's date: Wed Oct 14 2026"))
})

test("scrubEnv preserves surrounding text byte for byte", () => {
  const out = scrubEnv(CHUNK, "linux")
  assert.ok(out.startsWith("Today's date: Wed Oct 14 2026\n\nHere is some useful information"))
  assert.ok(out.endsWith("# Instructions\n"))
})

test("scrubEnv removes fields added by future versions (allowlist)", () => {
  const future = `${BEFORE.replace("</env>", "")}  Hostname: workstation-01\n  User: user\n</env>`
  const out = scrubEnv(future, "linux")
  assert.equal(out.includes("Hostname"), false)
  assert.equal(out.includes("User: user"), false)
  assert.ok(out.includes("Platform: linux"))
})

test("scrubEnv is idempotent", () => {
  const once = scrubEnv(CHUNK, "linux")
  assert.equal(scrubEnv(once, "linux"), once)
})

test("scrubEnv returns text without a block unchanged", () => {
  const text = "# Plain instructions\nNo environment here.\n"
  assert.equal(scrubEnv(text, "linux"), text)
})

test("markerOf trims leading blank lines and caps length", () => {
  const content = "\n\n# Security Policy — Mandatory Guardrails\n\n## Overview\n"
  assert.equal(markerOf(content), "# Security Policy — Mandatory Guardrails\n\n## Overview")
  assert.equal(markerOf(content, 8), "# Securi")
})

test("markers of distinct files do not collide", () => {
  const agents = "# Global Coding Preferences — Optimized for Multi-Agent Workflow\n\n## Tone\n"
  const policy = "# Security Policy — Mandatory Guardrails\n\n## Overview\n"
  assert.notEqual(markerOf(agents), markerOf(policy))
})
