"""Tests for the verified-parallelism path-overlap checker (C5, Inv 21)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from path_overlap import check, parse_groups

HOOK = Path(__file__).with_name("path_overlap.py")

SAMPLE = """\
# Roadmap
Parallel group: A
### Task: add auth
Files: src/auth/config.ts, src/auth/login.py

### Task: add db
Files: src/db/config.ts, src/db/migrate.py

Parallel group: B
### Task: fix ui
Files: src/ui/button.tsx
"""


def test_disjoint_paths_pass():
    messages, code = check(SAMPLE)
    assert code == 0
    assert messages == []


def test_duplicate_full_path_fails():
    text = SAMPLE.replace(
        "Files: src/db/config.ts, src/db/migrate.py",
        "Files: src/auth/config.ts, src/db/migrate.py",
    )
    messages, code = check(text)
    assert code == 1
    assert any(m.startswith("OVERLAP") for m in messages)


def test_basename_collision_is_not_overlap():
    text = SAMPLE.replace(
        "Files: src/db/config.ts, src/db/migrate.py",
        "Files: src/db/config.ts",
    )
    messages, code = check(text)
    assert code == 0


def test_missing_files_declaration_fails_closed():
    # A task in a parallel group without a Files: declaration must fail closed.
    text = SAMPLE.replace("\nFiles: src/db/config.ts, src/db/migrate.py", "")
    messages, code = check(text)
    assert code == 1
    assert any("has no Files: declaration" in m for m in messages)


def test_no_tasks_is_bad_input():
    messages, code = check("# Just a heading\n")
    assert code == 2
    assert messages == ["NO_TASKS: no parallel task groups with Files: declarations found"]


def test_files_outside_task_is_error():
    messages, code = check("Files: a.py\n")
    assert code == 2
    assert any("outside a task block" in m for m in messages)


def test_cli_with_file(tmp_path):
    path = tmp_path / "roadmap.md"
    path.write_text(SAMPLE)
    proc = subprocess.run(
        [sys.executable, str(HOOK), str(path)], capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_cli_with_overlap(tmp_path):
    path = tmp_path / "roadmap.md"
    path.write_text(SAMPLE.replace("src/db/config.ts", "src/auth/config.ts"))
    proc = subprocess.run(
        [sys.executable, str(HOOK), str(path)], capture_output=True, text=True
    )
    assert proc.returncode == 1
    assert "OVERLAP" in proc.stderr


def test_parse_groups_shape():
    groups, errors = parse_groups(SAMPLE)
    assert errors == []
    assert set(groups) == {"A", "B"}
    assert len(groups["A"]) == 2