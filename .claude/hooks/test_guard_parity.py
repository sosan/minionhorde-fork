"""Parity tests: the versioned guard matrix must hold on the Claude Code side.

The single source of truth is ``plugins/guard-audit/parity-matrix.json``
(shared with the OpenCode V2 plugin). Claude's PreToolUse guard is binary
(block / allow) — the ``ask`` layer lives in permission rules, not in the
hook — so matrix cases expected ``deny`` must be blocked here, and ``ask`` /
``allow`` cases must pass through (exit 0) for the permission layer to ask.
"""

from __future__ import annotations

import json
from pathlib import Path

from guard_pretooluse import evaluate

MATRIX = (
    Path(__file__).resolve().parents[2] / "plugins" / "guard-audit" / "parity-matrix.json"
)


def load_matrix() -> dict:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert matrix["version"] == "guard-audit-parity-v1", matrix["version"]
    assert len(matrix["cases"]) >= 7
    return matrix


def test_matrix_deny_cases_are_blocked():
    for case in load_matrix()["cases"]:
        if case["expected"] == "deny":
            blocked, reason = evaluate(case["input"])
            assert blocked, f"{case['id']}: expected block, got allow ({case['input']!r})"
            assert reason


def test_matrix_ask_and_allow_cases_pass_through():
    for case in load_matrix()["cases"]:
        if case["expected"] in {"ask", "allow"}:
            blocked, _ = evaluate(case["input"])
            assert not blocked, f"{case['id']}: hook must not block {case['expected']} case {case['input']!r}"
