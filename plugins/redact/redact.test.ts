import { test } from "node:test"
import assert from "node:assert/strict"
import { collectSecrets, makeRedactor } from "./redact.ts"

const DEFAULT_PATTERN_COUNT = 15

const FAKE_GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
const FAKE_OPENAI_KEY = "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef0"

test("collectSecrets reads sensitive env vars and skips noise", () => {
  const env = {
    GITHUB_TOKEN: FAKE_GITHUB_TOKEN,
    HOME: "/home/me",
    TERM: "xterm-256color",
    SHORT: "ab",
    ONLY_DIGITS: "12345",
    BOOLEAN: "true",
    DB_PASSWORD: "sw0rdfish",
  }
  const set = collectSecrets(env)
  assert.equal(set.count, 2)
  assert.match(String(set.literal), /sw0rdfish/)
  assert.match(String(set.literal), /ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/)
})

test("collectSecrets honors explicit secrets and patterns", () => {
  const set = collectSecrets({}, {
    secrets: ["my-custom-secret"],
    patterns: ["CUSTOM_[A-Z0-9]{8}"],
  })
  assert.equal(set.count, 1)
  assert.equal(set.patterns.length, DEFAULT_PATTERN_COUNT + 1)
  const r = makeRedactor(set)
  assert.equal(r.text("value=my-custom-secret end"), "value=[REDACTED_1] end")
  assert.equal(r.text("CUSTOM_ABCD1234"), "[REDACTED_2]")
})

test("redacts literal env secrets anywhere in text", () => {
  const r = makeRedactor(collectSecrets({ API_TOKEN: FAKE_GITHUB_TOKEN }))
  const out = r.text(`login with ${FAKE_GITHUB_TOKEN} please`)
  assert.equal(out, "login with [REDACTED_1] please")
  assert.ok(!out.includes(FAKE_GITHUB_TOKEN))
})

test("redacts known token patterns without env help", () => {
  const r = makeRedactor(collectSecrets({}))
  assert.equal(r.text(`key=${FAKE_OPENAI_KEY}`), "key=[REDACTED_1]")
  assert.equal(r.text(`duplicate sk-x ${FAKE_OPENAI_KEY}`), `duplicate sk-x [REDACTED_1]`)
})

test("redacts JWTs, private keys, auth headers and DB urls", () => {
  const r = makeRedactor(collectSecrets({}))
  const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
  assert.notEqual(r.text(`token ${jwt}`), `token ${jwt}`)
  assert.ok(r.text(`token ${jwt}`).includes("[REDACTED_"))

  const pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
  const pemOut = r.text(pem)
  assert.ok(!pemOut.includes("PRIVATE KEY"))
  assert.ok(!pemOut.includes("MIIEowIBAAKCAQEA"))

  assert.equal(
    r.text("Authorization: Bearer abcdefghij1234567890"),
    "Authorization: Bearer [REDACTED]",
  )
  assert.equal(
    r.text("postgres://admin:sw0rdfish@db.local:5432/app"),
    "postgres://[REDACTED]@db.local:5432/app",
  )
})

test("redacts string values under sensitive object keys", () => {
  const r = makeRedactor(collectSecrets({}))
  const input = { apiKey: "abc123", username: "alice", nested: [{ token: "xyz789" }] }
  r.value(input)
  assert.equal(input.apiKey, "[REDACTED_1]")
  assert.equal(input.username, "alice")
  assert.equal(input.nested[0].token, "[REDACTED_2]")
})

test("redacts message-style structures in place", () => {
  const r = makeRedactor(collectSecrets({}))
  const messages = [
    { role: "user", content: `my key is ${FAKE_OPENAI_KEY}` },
    { role: "assistant", content: [{ type: "text", text: "ok" }] },
  ]
  r.value(messages)
  assert.ok(messages[0].content.includes("[REDACTED_"))
  assert.ok(!messages[0].content.includes(FAKE_OPENAI_KEY))
  assert.equal(messages[1].content[0].text, "ok")
})

test("tokens are stable per secret and the result is idempotent", () => {
  const r = makeRedactor(collectSecrets({}))
  const first = r.text(`a ${FAKE_GITHUB_TOKEN} b ${FAKE_OPENAI_KEY}`)
  const second = r.text(`a ${FAKE_GITHUB_TOKEN} b ${FAKE_OPENAI_KEY}`)
  assert.equal(first, second)
  assert.equal(r.text(first), first)
  const parts = r.text(`${FAKE_GITHUB_TOKEN} vs ${FAKE_OPENAI_KEY}`).split(" ")
  assert.notEqual(parts[0], parts[2])
})

test("already-redacted tokens are preserved on re-redaction", () => {
  const r = makeRedactor(collectSecrets({}))
  assert.equal(r.text("already [REDACTED_5] here"), "already [REDACTED_5] here")
  assert.equal(r.text("[REDACTED_14] stays"), "[REDACTED_14] stays")
})

test("minSecretLength filters short env values", () => {
  const env = { TOKEN: "abcd" }
  assert.equal(collectSecrets(env, { minSecretLength: 8 }).count, 0)
  assert.equal(collectSecrets(env, { minSecretLength: 4 }).count, 1)
})

test("user-supplied regex flags are handled", () => {
  const r = makeRedactor(collectSecrets({}, { patterns: ["(?i)XSA_[a-z0-9]{6}"] }))
  assert.equal(r.text("xsa_abc123!"), "[REDACTED_1]!")
})