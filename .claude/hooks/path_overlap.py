#!/usr/bin/env python3
"""Verified parallelism: full-file-path overlap check (CORE Inv 21).

Reads a roadmap or planning document containing parallel task groups with
`Files:` declarations and rejects overlapping FULL paths. Basenames are not
compared: `src/auth/config.ts` and `src/db/config.ts` are disjoint.
Missing declarations fail closed — absence is not evidence of disjointness.

Input format (one or more task blocks):

    Parallel group: A
    ### Task: add auth
    Files: src/auth/config.ts, src/auth/login.py

    ### Task: add db
    Files: src/db/config.ts, src/db/migrate.py

Usage:
    path-overlap.py <file>            # exit 0 clean, 1 overlap, 2 bad input
    path-overlap.py --text <text>     # same, from literal text

The gate integration passes the roadmap path explicitly; the script never
guesses a file.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

GROUP_RE = re.compile(r"^Parallel group:\s*(.+?)\s*$", re.I)
TASK_RE = re.compile(r"^#{2,4}\s*(?:Task|Phase|Step)\b[:\s]*(.*?)\s*$", re.I)
FILES_RE = re.compile(r"^Files:\s*(.+?)\s*$", re.I)


def parse_groups(text: str) -> tuple[dict[str, list[tuple[str, list[str]]]], list[str]]:
    """Return {group: [(task_name, [full paths])]} and input errors."""
    groups: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    errors: list[str] = []
    current_group = "(default)"
    current_task: str | None = None
    task_has_files = False

    def flush() -> None:
        nonlocal current_task, task_has_files
        if current_task is not None and not task_has_files:
            errors.append(f"task '{current_task}' in group '{current_group}' has no Files: declaration")
        current_task = None
        task_has_files = False

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if m := GROUP_RE.match(line):
            flush()
            current_group = m.group(1)
            continue
        if m := TASK_RE.match(line):
            flush()
            current_task = m.group(1) or f"task@{lineno}"
            groups[current_group].append((current_task, []))
            continue
        if m := FILES_RE.match(line):
            if current_task is None:
                errors.append(f"line {lineno}: Files: outside a task block")
                continue
            task_has_files = True
            paths = [p.strip() for p in m.group(1).split(",") if p.strip()]
            if not paths:
                errors.append(f"task '{current_task}' has an empty Files: declaration")
            groups[current_group][-1] = (current_task, paths)

    flush()
    return groups, errors


def check(text: str) -> tuple[list[str], int]:
    """Return (messages, exit code)."""
    groups, errors = parse_groups(text)
    messages = list(errors)
    for group, tasks in sorted(groups.items()):
        if len(tasks) < 2:
            continue
        seen: dict[str, str] = {}
        for task_name, paths in tasks:
            for path in paths:
                if path in seen and seen[path] != task_name:
                    messages.append(
                        f"OVERLAP group '{group}': {path} in '{seen[path]}' and '{task_name}'"
                    )
                else:
                    seen[path] = task_name
    if not groups:
        messages.append("NO_TASKS: no parallel task groups with Files: declarations found")
        return messages, 2
    return messages, (1 if any(m.startswith("OVERLAP") for m in messages) or errors else 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="roadmap or planning file")
    group.add_argument("--text", help="literal roadmap text")
    args = parser.parse_args(argv)

    if args.text is not None:
        text = args.text
    else:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"INPUT_ERROR: {exc}", file=sys.stderr)
            return 2

    messages, code = check(text)
    for message in messages:
        print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
