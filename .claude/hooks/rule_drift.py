#!/usr/bin/env python3
"""Rule-drift checker for the instruction stack.

Marked fragments must stay synchronized with their canonical source.

Marker format (HTML comment lines in Markdown files):

    <!-- @rule:<name> @source:<canonical-path> @fragment:<id> -->
    shared normative content
    <!-- /@rule:<name> -->

Conventions:
- The canonical block lives in the file named by @source and repeats the same
  @rule with @source pointing to itself.
- Every other block with the same @rule must canonicalize to the same content
  as the canonical block in the source file.
- A block without @source is ORPHAN_FAIL.
- An @source file that does not exist, or that lacks the referenced rule, is
  SOURCE_MISSING.

Exit codes: 0 = consistent; 1 = drift/orphan/missing; 2 = usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

OPEN_RE = re.compile(r"<!--\s*@rule:([A-Za-z0-9_.-]+)\s+(.*?)-->", re.S)
CLOSE_RE = re.compile(r"<!--\s*/@rule:")
DEFAULT_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    ".claude/rules/DOGMAS-CORE.md",
    ".claude/rules/DOGMAS-REF-seed.md",
    ".claude/rules/security.md",
    ".claude/rules/testing.md",
    ".claude/rules/workflow.md",
]


def canonicalize(lines: list[str]) -> str:
    """Whitespace-insensitive canonical form of a fragment."""
    parts = []
    for line in lines:
        text = " ".join(line.split())
        if text:
            parts.append(text)
    return " ".join(parts)


def parse_blocks(path: Path) -> tuple[list[dict], list[str]]:
    """Return (blocks, errors) for one file."""
    blocks: list[dict] = []
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return blocks, [f"{path}: unreadable ({exc})"]

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = OPEN_RE.search(lines[i])
        if not match:
            i += 1
            continue
        rule = match.group(1)
        attrs = {}
        for token in match.group(2).split():
            if ":" in token:
                key, value = token.split(":", 1)
                attrs[key.lstrip("@").strip()] = value.strip()
        j = i + 1
        content_lines: list[str] = []
        closed = False
        while j < len(lines):
            if CLOSE_RE.search(lines[j]):
                closed = True
                break
            content_lines.append(lines[j])
            j += 1
        if not closed:
            errors.append(f"{path}:{i + 1}: unterminated @rule block '{rule}'")
            break
        blocks.append(
            {
                "file": str(path),
                "rule": rule,
                "source": attrs.get("source", ""),
                "fragment": attrs.get("fragment", ""),
                "content": canonicalize(content_lines),
                "line": i + 1,
            }
        )
        i = j + 1
    return blocks, errors


def collect_files(args: argparse.Namespace) -> tuple[list[Path], list[str]]:
    errors: list[str] = []
    if args.files:
        return [Path(p) for p in args.files], errors
    if args.changed:
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            return [], [f"git diff failed: {exc}"]
        names = [n for n in out.stdout.splitlines() if n.endswith(".md")]
        return [Path(n) for n in names], errors
    return [Path(p) for p in DEFAULT_FILES], errors


def check(files: list[Path]) -> tuple[list[str], int]:
    """Return (messages, exit_code)."""
    messages: list[str] = []
    failures = 0
    all_blocks: list[dict] = []
    for path in files:
        blocks, errors = parse_blocks(path)
        messages.extend(errors)
        failures += len(errors)
        all_blocks.extend(blocks)

    by_rule: dict[str, list[dict]] = {}
    for block in all_blocks:
        by_rule.setdefault(block["rule"], []).append(block)

    for rule, blocks in sorted(by_rule.items()):
        # Canonical block: @source equals its own file.
        canonical = next(
            (b for b in blocks if b["source"] and Path(b["source"]) == Path(b["file"])),
            None,
        )
        if canonical is None:
            # Fall back: canonical content lives in the @source file's own block.
            source_path = blocks[0]["source"]
            if not source_path:
                for block in blocks:
                    messages.append(
                        f"ORPHAN_FAIL {block['file']}:{block['line']} "
                        f"rule '{rule}' has no @source"
                    )
                    failures += 1
                continue
            source_file = Path(source_path)
            if not source_file.is_file():
                for block in blocks:
                    messages.append(
                        f"SOURCE_MISSING {block['file']}:{block['line']} "
                        f"rule '{rule}' -> {source_path}"
                    )
                    failures += 1
                continue
            source_blocks, source_errors = parse_blocks(source_file)
            messages.extend(source_errors)
            failures += len(source_errors)
            candidates = [b for b in source_blocks if b["rule"] == rule]
            if not candidates:
                for block in blocks:
                    messages.append(
                        f"SOURCE_MISSING {block['file']}:{block['line']} "
                        f"rule '{rule}' not found in {source_path}"
                    )
                    failures += 1
                continue
            canonical = candidates[0]

        canonical_hash = hashlib.sha256(canonical["content"].encode("utf-8")).hexdigest()
        for block in blocks:
            if block is canonical:
                continue
            block_hash = hashlib.sha256(block["content"].encode("utf-8")).hexdigest()
            if block_hash != canonical_hash:
                messages.append(
                    f"DRIFT_FAIL {block['file']}:{block['line']} rule '{rule}' "
                    f"diverges from canonical {canonical['file']}:{canonical['line']}"
                )
                failures += 1

    if not all_blocks and not messages:
        messages.append("no marked rules found (nothing to verify)")
    return messages, (1 if failures else 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all", action="store_true", help="check the default instruction files"
    )
    group.add_argument(
        "--changed",
        action="store_true",
        help="check only Markdown files changed vs HEAD",
    )
    parser.add_argument("files", nargs="*", help="explicit files to check")
    args = parser.parse_args(argv)

    if not args.all and not args.changed and not args.files:
        parser.error("choose --all, --changed, or explicit files")

    files, errors = collect_files(args)
    messages, code = check(files)
    for message in messages:
        print(message)
    return 2 if errors and not files else code


if __name__ == "__main__":
    sys.exit(main())
