#!/usr/bin/env bash
set -euo pipefail

# Formats the file that was just written or edited. Missing formatters are a
# no-op: the hook never blocks an edit because a tool is not installed.
input=$(cat)
file_path=$(printf '%s' "$input" | python3 -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))' \
  2>/dev/null || true)

[ -n "$file_path" ] || exit 0
[ -f "$file_path" ] || exit 0

case "$file_path" in
  *.py)
    black --quiet "$file_path" >/dev/null 2>&1 || true
    ;;
  *.js|*.jsx|*.ts|*.tsx|*.css)
    npx --no-install prettier --write "$file_path" >/dev/null 2>&1 || true
    ;;
  *.go)
    gofmt -w "$file_path" >/dev/null 2>&1 || true
    ;;
esac
