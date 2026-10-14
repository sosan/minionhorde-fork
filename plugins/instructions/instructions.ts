// Instructions plugin engine — pure module (no OpenCode imports) so it can be
// unit-tested with `node --test`.

/** Delimiter of the environment block OpenCode injects into the system prompt. */
export const ENV_BLOCK = /<env>[\s\S]*?<\/env>/

/**
 * Replacement for the environment block: same delimiter, fixed content.
 *
 * `Platform` is the only field kept. It is operationally useful — it tells the
 * model which shell dialect, path separators and binaries to expect — and it
 * identifies nobody. Everything else OpenCode emits inside `<env>` is dropped:
 * working directory, workspace root, git detection, the temp-dir hint, and
 * anything a future version adds.
 *
 * @param platform - Value of `process.platform`.
 * @returns The controlled block. Byte-identical on every call.
 *
 * @example
 * controlledEnv("linux");
 * // => "<env>\n  Platform: linux\n</env>"
 */
export function controlledEnv(platform: string): string {
  return `<env>\n  Platform: ${platform}\n</env>`
}

/**
 * Rewrites the environment block inside a system-prompt chunk.
 *
 * This is an allowlist by construction: only what {@link controlledEnv} emits
 * survives, no matter how many fields OpenCode puts inside `<env>` — including
 * ones that do not exist yet. Text without a block is returned unchanged, so
 * the function is safe to run on every request.
 *
 * The surrounding text — including the `Today's date:` instruction, which
 * OpenCode emits as a separate source *outside* `<env>` — is left untouched.
 *
 * @param text - A chunk of the assembled system prompt.
 * @param platform - Value of `process.platform`.
 * @returns The chunk with its environment block replaced.
 *
 * @example
 * scrubEnv("Today's date: X\n\n<env>\n  Working directory: /home/me\n</env>", "linux");
 * // => "Today's date: X\n\n<env>\n  Platform: linux\n</env>"
 */
export function scrubEnv(text: string, platform: string): string {
  return text.replace(ENV_BLOCK, controlledEnv(platform))
}

/**
 * Marker used to detect whether an instruction file is already present in the
 * system prompt, so the plugin never injects the same file twice.
 *
 * OpenCode loads `AGENTS.md` natively. Without this check the plugin would
 * append it a second time on top of its own injection.
 *
 * @param content - Full text of the instruction file.
 * @param length - Number of leading characters to use. Default 64.
 * @returns The first `length` non-blank characters of the file.
 *
 * @example
 * markerOf("# Security Policy — Mandatory Guardrails\n\n## Overview\n");
 * // => "# Security Policy — Mandatory Guardrails\n\n## Overview"
 */
export function markerOf(content: string, length = 64): string {
  return content.trim().slice(0, length)
}
