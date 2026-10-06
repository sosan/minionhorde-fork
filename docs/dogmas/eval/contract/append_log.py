"""Ordered concurrent append log with crash recovery (task 10.26).

The journal is a JSON-lines file where each entry carries the hash of the
previous entry, building a verifiable chain. A sidecar manifest stores
the last valid sequence and head hash; the manifest itself is hashed so
tampering is detectable. On recovery:

* a valid manifest truncates the journal at ``last_sequence`` and marks
  anything beyond as aborted (incomplete writes, partial lines);
* a tampered or missing manifest triggers a full journal rescan, with
  status ``rescanned`` recorded in the rebuilt manifest;
* hash-chain breaks are marked aborted and never recovered.

Concurrent appends are serialized by a lock. The journal file and the
manifest are both persisted via atomic temp-file replace so a crash
mid-write never leaves a half-written manifest behind.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import digest


class AppendLogError(Exception):
    """Raised when an append cannot be committed atomically."""


@dataclass(frozen=True)
class AppendEntry:
    sequence: int
    entry_type: str
    payload: dict
    previous_hash: str
    entry_hash: str


def _hash_entry(sequence: int, entry_type: str, payload: dict, previous_hash: str) -> str:
    return digest(
        {
            "sequence": sequence,
            "entry_type": entry_type,
            "payload": payload,
            "previous_hash": previous_hash,
        }
    )


def _hash_manifest(last_sequence: int, status: str, head_hash: str) -> str:
    return digest(
        {"last_sequence": last_sequence, "status": status, "head_hash": head_hash}
    )


def _entry_line(entry: AppendEntry) -> str:
    return json.dumps(
        {
            "sequence": entry.sequence,
            "entry_type": entry.entry_type,
            "payload": entry.payload,
            "previous_hash": entry.previous_hash,
            "entry_hash": entry.entry_hash,
        },
        ensure_ascii=False,
    )


class AppendLog:
    """Append-only journal with chained hashing and atomic manifest."""

    def __init__(self, journal_path: Path, *, manifest_path: Path | None = None) -> None:
        self.journal_path = Path(journal_path)
        self.manifest_path = (
            Path(manifest_path) if manifest_path is not None else self.journal_path.with_suffix(".manifest.json")
        )
        self._lock = threading.Lock()
        self.entries: list[AppendEntry] = []
        self.head_hash: str = ""
        self._load()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def append(self, entry_type: str, payload: dict[str, Any]) -> AppendEntry:
        with self._lock:
            sequence = len(self.entries)
            previous_hash = self.entries[-1].entry_hash if self.entries else ""
            entry_hash = _hash_entry(sequence, entry_type, payload, previous_hash)
            entry = AppendEntry(
                sequence=sequence,
                entry_type=entry_type,
                payload=payload,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
            )
            self._atomic_append_line(entry)
            self.entries.append(entry)
            self.head_hash = entry.entry_hash
            self._write_manifest(last_sequence=sequence, status="valid", head_hash=entry.entry_hash)
            return entry

    def verify_chain(self) -> bool:
        previous = ""
        for entry in self.entries:
            if entry.previous_hash != previous:
                return False
            if entry.entry_hash != _hash_entry(
                entry.sequence, entry.entry_type, entry.payload, entry.previous_hash
            ):
                return False
            previous = entry.entry_hash
        return True

    @classmethod
    def recover(cls, journal_path: Path, manifest_path: Path) -> dict[str, Any]:
        journal = Path(journal_path)
        manifest_file = Path(manifest_path)

        manifest: dict[str, Any] | None = None
        manifest_valid = False
        if manifest_file.exists():
            try:
                raw = json.loads(manifest_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = None
            if raw is not None:
                expected = raw.get("manifest_hash")
                body = {
                    "last_sequence": raw.get("last_sequence"),
                    "status": raw.get("status"),
                    "head_hash": raw.get("head_hash"),
                }
                if expected == _hash_manifest(
                    body["last_sequence"], body["status"], body["head_hash"]
                ):
                    manifest = raw
                    manifest_valid = True

        lines = (
            journal.read_text(encoding="utf-8").splitlines()
            if journal.exists() and journal.stat().st_size > 0
            else []
        )

        recovered: list[AppendEntry] = []
        aborted: list[dict[str, Any]] = []
        prefix_end = manifest["last_sequence"] if manifest_valid else None

        for index, line in enumerate(lines):
            if prefix_end is not None and index > prefix_end:
                aborted.append({"sequence": None, "reason": "incomplete_write"})
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                aborted.append({"sequence": None, "reason": "incomplete_write"})
                continue
            expected_prev = recovered[-1].entry_hash if recovered else ""
            if data.get("previous_hash", "") != expected_prev:
                aborted.append(
                    {"sequence": data.get("sequence"), "reason": "hash_mismatch"}
                )
                continue
            sequence = data["sequence"]
            entry_type = data["entry_type"]
            payload = data["payload"]
            previous_hash = data["previous_hash"]
            entry_hash = data["entry_hash"]
            expected_hash = _hash_entry(sequence, entry_type, payload, previous_hash)
            if entry_hash != expected_hash:
                aborted.append({"sequence": sequence, "reason": "hash_mismatch"})
                continue
            recovered.append(
                AppendEntry(
                    sequence=sequence,
                    entry_type=entry_type,
                    payload=payload,
                    previous_hash=previous_hash,
                    entry_hash=entry_hash,
                )
            )

        if recovered:
            new_last = recovered[-1].sequence
            new_head = recovered[-1].entry_hash
        else:
            new_last = -1
            new_head = ""

        new_status = "valid" if manifest_valid else "rescanned"
        new_manifest = {
            "last_sequence": new_last,
            "status": new_status,
            "head_hash": new_head,
        }
        new_manifest["manifest_hash"] = _hash_manifest(
            new_manifest["last_sequence"], new_manifest["status"], new_manifest["head_hash"]
        )

        cls._persist(journal, manifest_file, recovered, new_manifest)

        return {
            "recovered": list(recovered),
            "aborted": aborted,
            "manifest": new_manifest,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.journal_path.exists() or self.journal_path.stat().st_size == 0:
            return
        result = self.recover(self.journal_path, self.manifest_path)
        self.entries = list(result["recovered"])
        self.head_hash = self.entries[-1].entry_hash if self.entries else ""

    def _atomic_append_line(self, entry: AppendEntry) -> None:
        # The journal is append-only: never rewrite the file. A crash
        # mid-write leaves (at most) a truncated trailing line, which
        # recovery detects as an incomplete write.
        line = _entry_line(entry) + "\n"
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def _write_manifest(self, *, last_sequence: int, status: str, head_hash: str) -> None:
        body = {"last_sequence": last_sequence, "status": status, "head_hash": head_hash}
        body["manifest_hash"] = _hash_manifest(
            body["last_sequence"], body["status"], body["head_hash"]
        )
        tmp = self.manifest_path.with_suffix(self.manifest_path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.manifest_path)

    @classmethod
    def _persist(
        cls,
        journal: Path,
        manifest_file: Path,
        recovered: list[AppendEntry],
        manifest: dict[str, Any],
    ) -> None:
        text = "".join(_entry_line(entry) + "\n" for entry in recovered)
        tmp_journal = journal.with_suffix(journal.suffix + ".recover.tmp")
        with open(tmp_journal, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_journal, journal)

        tmp_manifest = manifest_file.with_suffix(manifest_file.suffix + ".tmp")
        with open(tmp_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_manifest, manifest_file)
