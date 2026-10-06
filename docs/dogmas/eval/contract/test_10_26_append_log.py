"""Tests for task 10.26 — ordered concurrent appends with crash recovery.

The append log MUST serialize concurrent appends (lock), chain entries
with hashes, persist an atomic manifest, and on recovery retain the last
valid manifest while marking incomplete trailing writes aborted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.append_log import AppendLog, AppendLogError


def test_append_orders_entries_and_chains_hashes(tmp_path: Path) -> None:
    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    a = log.append("turn", {"sequence_label": "first"})
    b = log.append("state", {"sequence_label": "second"})
    assert a.sequence == 0
    assert b.sequence == 1
    assert b.previous_hash == a.entry_hash
    assert log.head_hash == b.entry_hash
    assert log.verify_chain()


def test_append_is_atomic_and_persisted(tmp_path: Path) -> None:
    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    log.append("turn", {"n": 1})
    log.append("turn", {"n": 2})
    manifest = json.loads(log.manifest_path.read_text(encoding="utf-8"))
    assert manifest["last_sequence"] == 1
    assert manifest["status"] == "valid"
    assert len(log.entries) == 2


def test_recovery_retains_last_valid_manifest_after_crash(tmp_path: Path) -> None:
    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    log.append("turn", {"n": 1})
    log.append("turn", {"n": 2})
    # Simulate a crash: a partial trailing write lands in the journal
    # after the last valid entry (manifest still points at entry 1).
    with open(log.journal_path, "a", encoding="utf-8") as f:
        f.write('{"sequence": 2, "entry_type": "turn", "payload": {"n": 3}, "previous_hash": "')
    recovered = AppendLog.recover(log.journal_path, log.manifest_path)
    assert len(recovered["recovered"]) == 2
    assert len(recovered["aborted"]) == 1
    assert recovered["aborted"][0]["reason"] == "incomplete_write"
    assert recovered["manifest"]["last_sequence"] == 1
    assert recovered["manifest"]["status"] == "valid"


def test_recovery_marks_hash_mismatch_as_corrupted_not_recovered(tmp_path: Path) -> None:
    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    log.append("turn", {"n": 1})
    log.append("turn", {"n": 2})
    # Corrupt the second entry in place.
    lines = log.journal_path.read_text(encoding="utf-8").splitlines()
    bad = json.loads(lines[1])
    bad["payload"] = {"n": 999}
    lines[1] = json.dumps(bad)
    log.journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    recovered = AppendLog.recover(log.journal_path, log.manifest_path)
    assert len(recovered["recovered"]) == 1
    assert recovered["aborted"][0]["reason"] == "hash_mismatch"


def test_manifest_hash_mismatch_falls_back_to_journal_rescan(tmp_path: Path) -> None:
    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    log.append("turn", {"n": 1})
    log.append("turn", {"n": 2})
    # Tamper with the manifest (change last_sequence).
    manifest = json.loads(log.manifest_path.read_text(encoding="utf-8"))
    manifest["last_sequence"] = 99
    log.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    recovered = AppendLog.recover(log.journal_path, log.manifest_path)
    assert len(recovered["recovered"]) == 2
    assert recovered["manifest"]["status"] == "rescanned"


def test_concurrent_appends_are_serialized(tmp_path: Path) -> None:
    import threading

    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    errors: list[Exception] = []

    def writer(start: int, count: int) -> None:
        try:
            for i in range(start, start + count):
                log.append("turn", {"writer": start, "i": i})
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(0, 25)), threading.Thread(target=writer, args=(100, 25))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert log.verify_chain()
    assert len(log.entries) == 50
    sequences = [entry.sequence for entry in log.entries]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == 50


def test_append_after_recovery_rejects_aborted_entries(tmp_path: Path) -> None:
    log = AppendLog(tmp_path / "journal.log", manifest_path=tmp_path / "manifest.json")
    log.append("turn", {"n": 1})
    with open(log.journal_path, "a", encoding="utf-8") as f:
        f.write('{"sequence": 1, "entry_type": "turn", "payload": {"n": 2}, "previous_hash": "')
    recovered = AppendLog.recover(log.journal_path, log.manifest_path)
    assert len(recovered["aborted"]) == 1
    # A new append after recovery continues from the last valid entry.
    log2 = AppendLog(log.journal_path, manifest_path=log.manifest_path)
    log2.append("turn", {"n": 3})
    assert log2.entries[-1].sequence == 1