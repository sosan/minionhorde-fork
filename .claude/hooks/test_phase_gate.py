"""Tests for the explicit phase gate (C4).

Runs `.claude/hooks/phase-gate.sh` as a subprocess in CLI mode and in
UserPromptSubmit (stdin JSON) mode, with an isolated CLAUDE_PROJECT_DIR.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).with_name("phase-gate.sh")


def run_cli(phase: str, project: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HOOK), phase],
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), **(extra_env or {})},
    )


def run_prompt(prompt: str, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
    )


def make_tier1(project: Path) -> None:
    (project / "docs" / "specs").mkdir(parents=True)
    (project / "docs" / "PRD.md").write_text("# PRD\n")
    (project / "docs" / "specs" / "a.md").write_text("# Spec\n")


def test_cli_passes_for_tier0(tmp_path):
    proc = run_cli("tier0", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: tier0" in proc.stdout


def test_cli_phase2_fails_without_prd(tmp_path):
    proc = run_cli("tier1_phase2", tmp_path)
    assert proc.returncode == 2
    assert "PHASE_GATE_FAIL" in proc.stderr


def test_cli_phase2_passes_with_prd_and_spec(tmp_path):
    make_tier1(tmp_path)
    proc = run_cli("tier1_phase2", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: tier1_phase2" in proc.stdout


def test_unknown_phase_fails_loudly(tmp_path):
    proc = run_cli("tier9_fase_x", tmp_path)
    assert proc.returncode == 2
    assert "unknown phase" in proc.stderr


def test_natural_language_mention_does_not_gate(tmp_path):
    proc = run_prompt("avanza a la fase 2 del proyecto", tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_prose_mentioning_the_marker_does_not_gate(tmp_path):
    proc = run_prompt("the /gate tier1_phase2 hook is broken in this repo", tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_marker_blocks_when_prerequisite_missing(tmp_path):
    proc = run_prompt("/gate tier1_phase2", tmp_path)
    assert proc.returncode == 2
    assert "PHASE_GATE_FAIL" in proc.stderr


def test_marker_and_cli_parity(tmp_path):
    make_tier1(tmp_path)
    cli = run_cli("tier1_phase2", tmp_path)
    marker = run_prompt("/gate tier1_phase2", tmp_path)
    assert cli.returncode == marker.returncode == 0
    assert "PHASE_GATE_PASS: tier1_phase2" in cli.stdout
    assert "PHASE_GATE_PASS: tier1_phase2" in marker.stdout


def test_marker_on_its_own_line_works(tmp_path):
    proc = run_prompt("please advance\n/gate tier0\nthanks", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: tier0" in proc.stdout


def test_empty_prompt_passes_silently(tmp_path):
    proc = run_prompt("", tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_tier2_requires_spec(tmp_path):
    assert run_cli("tier2_phase1", tmp_path).returncode == 2
    make_tier1(tmp_path)
    proc = run_cli("tier2_phase1", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: tier2_phase1" in proc.stdout


def test_tier2_phase2_requires_tests(tmp_path):
    make_tier1(tmp_path)
    assert run_cli("tier2_phase2", tmp_path).returncode == 2
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert False\n")
    assert run_cli("tier2_phase2", tmp_path).returncode == 0


def test_tier3_phase1_only_requires_docs(tmp_path):
    assert run_cli("tier3_phase1", tmp_path).returncode == 2
    (tmp_path / "docs").mkdir()
    assert run_cli("tier3_phase1", tmp_path).returncode == 0


def test_tier3_phase2_requires_a_regression_test(tmp_path):
    (tmp_path / "docs").mkdir()
    assert run_cli("tier3_phase2", tmp_path).returncode == 2
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_bug.py").write_text("def test_bug():\n    assert False\n")
    assert run_cli("tier3_phase2", tmp_path).returncode == 0


def test_optional_red_test_check_blocks_green_suite(tmp_path):
    make_tier1(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    proc = run_cli("tier1_phase3", tmp_path, {"CLAUDE_TEST_CMD": "true"})
    assert proc.returncode == 2
    assert "expected red" in proc.stderr

    proc = run_cli("tier1_phase3", tmp_path, {"CLAUDE_TEST_CMD": "false"})
    assert proc.returncode == 0


def write_roadmap(project: Path, text: str) -> None:
    (project / "docs").mkdir(exist_ok=True)
    (project / "docs" / "IMPLEMENTATION_ROADMAP.md").write_text(text, encoding="utf-8")


def test_parallelism_gate_passes_on_disjoint_paths(tmp_path):
    write_roadmap(
        tmp_path,
        "Parallel group: A\n"
        "### Task: auth\nFiles: src/auth/a.py\n\n"
        "### Task: db\nFiles: src/db/b.py\n",
    )
    proc = run_cli("parallelism", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: parallelism" in proc.stdout


def test_parallelism_gate_fails_on_overlap(tmp_path):
    write_roadmap(
        tmp_path,
        "Parallel group: A\n"
        "### Task: auth\nFiles: src/shared/x.py\n\n"
        "### Task: db\nFiles: src/shared/x.py\n",
    )
    proc = run_cli("parallelism", tmp_path)
    assert proc.returncode == 2
    assert "PHASE_GATE_FAIL" in proc.stderr


def test_parallelism_gate_fails_without_plan(tmp_path):
    proc = run_cli("parallelism", tmp_path)
    assert proc.returncode == 2
    assert "parallelism plan not found" in proc.stderr
