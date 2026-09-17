#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[ -n "$file_path" ] || exit 0

case "$file_path" in
    *.py)
    black --quiet "$file_path" 2>/dev/null || true
    ;;
    *.js|*.ts|*.jsx|*.tsx)
    npx prettier --write "$file_path" 2>/dev/null || true
    ;;
    *.go)
    gofmt -w "$file_path" 2>/dev/null || true
    ;;
esac
