"""Tests for the evaluation exercise-manifest validator (C6)."""
from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / ".git").exists())
VALIDATOR = REPO_ROOT / "docs" / "dogmas" / "eval" / "check_manifest.py"
MANIFEST = REPO_ROOT / "docs" / "dogmas" / "eval" / "exercise-manifest.json"

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("check_manifest", VALIDATOR)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_real_manifest_passes_cli():
    proc = subprocess.run([sys.executable, str(VALIDATOR)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "manifest matches the import graph" in proc.stdout


def test_manifest_matches_measured_reachability():
    m = load_manifest()
    messages, code = cm.validate(m)
    assert code == 0
    assert messages == ["manifest matches the import graph and restrictions hold"]


def test_declared_synthetic_but_not_reachable_fails():
    m = load_manifest()
    m["contracts"]["comparability"] = "synthetic_run"
    messages, code = cm.validate(m)
    assert code == 1
    assert any("comparability" in msg and "synthetic_run" in msg for msg in messages)


def test_declared_test_only_but_reachable_fails():
    m = load_manifest()
    m["contracts"]["ingest_manual"] = "test_only"
    messages, code = cm.validate(m)
    assert code == 1
    assert any("ingest_manual" in msg for msg in messages)


def test_unregistered_module_fails():
    m = load_manifest()
    # Remove a real contract entry to simulate an unregistered module.
    m["contracts"].pop("providers")
    messages, code = cm.validate(m)
    assert code == 1
    assert any("UNREGISTERED" in msg and "providers" in msg for msg in messages)


def test_declared_file_that_does_not_exist_fails():
    m = load_manifest()
    m["contracts"]["ghost_module"] = "test_only"
    messages, code = cm.validate(m)
    assert code == 1
    assert any("UNREGISTERED_FILE" in msg and "ghost_module" in msg for msg in messages)


def test_missing_entrypoint_kind_fails():
    m = load_manifest()
    m["entrypoints"][0]["kind"] = "nonexistent_kind"
    messages, code = cm.validate(m)
    assert code == 1
    assert any("unknown kind" in msg for msg in messages)


def test_from_contract_import_parsing(tmp_path, monkeypatch):
    # Build a tiny contract dir with from-contract-import edge.
    fake = tmp_path / "contract"
    fake.mkdir()
    (fake / "providers.py").write_text("x = 1\n")
    (fake / "runner.py").write_text("from contract import providers\n")
    monkeypatch.setattr(cm, "CONTRACT_DIR", fake)
    imports = cm._module_imports(fake / "runner.py")
    assert "providers" in imports


def test_from_dot_module_import_parsing(tmp_path, monkeypatch):
    fake = tmp_path / "contract"
    fake.mkdir()
    (fake / "canonical.py").write_text("x = 1\n")
    (fake / "runner.py").write_text("from .canonical import digest\n")
    monkeypatch.setattr(cm, "CONTRACT_DIR", fake)
    imports = cm._module_imports(fake / "runner.py")
    assert "canonical" in imports

def test_manifest_requires_content_hash():
    m = load_manifest()
    m.pop("manifest_sha256")
    messages, code = cm.validate(m)
    assert code == 1
    assert any("HASH_MISSING" in msg for msg in messages)


def test_manifest_tamper_changes_hash():
    m = load_manifest()
    m["contracts"]["p2_1"] = "synthetic_run"
    messages, code = cm.validate(m)
    assert code == 1
    assert any("HASH_MISMATCH" in msg for msg in messages)


def test_manifest_hash_is_stable():
    m = load_manifest()
    assert m["manifest_sha256"] == cm.manifest_hash(m)


def test_from_contract_dot_import_parsing(tmp_path, monkeypatch):
    fake = tmp_path / "contract"
    fake.mkdir()
    (fake / "schema_store.py").write_text("x = 1\n")
    (fake / "runner.py").write_text("from contract.schema_store import SchemaStore\n")
    monkeypatch.setattr(cm, "CONTRACT_DIR", fake)
    imports = cm._module_imports(fake / "runner.py")
    assert "schema_store" in imports