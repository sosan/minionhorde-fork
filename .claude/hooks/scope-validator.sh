#!/usr/bin/env bash
# Backwards-compatible wrapper. The implementation lives in scope_validator.py.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scope_validator.py"
