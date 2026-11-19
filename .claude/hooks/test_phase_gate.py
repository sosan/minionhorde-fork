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


def run_cli(phase: str, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HOOK), phase],
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
    )


def run_prompt(prompt: str, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
    )


def test_cli_passes_for_tier0(tmp_path):
    proc = run_cli("tier0", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: tier0" in proc.stdout


def test_cli_phase2_fails_without_prd(tmp_path):
    proc = run_cli("tier1_phase2", tmp_path)
    assert proc.returncode == 2
    assert "PHASE_GATE_FAIL" in proc.stderr


def test_cli_phase2_passes_with_prd_and_spec(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PRD.md").write_text("# PRD\n")
    (tmp_path / "docs" / "specs").mkdir()
    (tmp_path / "docs" / "specs" / "a.md").write_text("# Spec\n")
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


def test_marker_blocks_when_prerequisite_missing(tmp_path):
    proc = run_prompt("/gate tier1_phase2", tmp_path)
    assert proc.returncode == 2
    assert "PHASE_GATE_FAIL" in proc.stderr


def test_marker_and_cli_parity(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PRD.md").write_text("# PRD\n")
    (tmp_path / "docs" / "specs").mkdir()
    (tmp_path / "docs" / "specs" / "a.md").write_text("# Spec\n")
    cli = run_cli("tier1_phase2", tmp_path)
    marker = run_prompt("/gate tier1_phase2", tmp_path)
    assert cli.returncode == marker.returncode == 0
    assert "PHASE_GATE_PASS: tier1_phase2" in cli.stdout
    assert "PHASE_GATE_PASS: tier1_phase2" in marker.stdout


def test_marker_inside_sentence_works(tmp_path):
    proc = run_prompt("por favor avanza /gate tier0 ya", tmp_path)
    assert proc.returncode == 0
    assert "PHASE_GATE_PASS: tier0" in proc.stdout


def test_empty_prompt_passes_silently(tmp_path):
    proc = run_prompt("", tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == ""