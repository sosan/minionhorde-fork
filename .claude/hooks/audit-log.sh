#!/usr/bin/env bash
# Backwards-compatible wrapper. The implementation lives in audit_log.py.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/audit_log.py" "$@"
