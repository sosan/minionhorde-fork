"""Evidence custody lifecycle and artifact hash resolution.

This module owns evidence-reference integrity for the evaluation contract. It
creates custody records for evidence artifacts, verifies that referenced
artifacts still exist and hash-match, and enforces frozen-record immutability
plus stored-literal expiry without inferring provenance that the caller did
not supply.

Custody states are exactly:

    OPEN        evidence recorded, still eligible for amendment
    FROZEN      evidence locked; content and hashes immutable
    AMENDED     a superseded record replaced by a newer amendment
    SUPERSEDED  a record replaced by a later authoritative record
    CORRUPTED   stored content no longer matches its recorded hash

The module never mutates the artifacts it describes. Resolution is read-only:
it recomputes hashes and compares them to the custody record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

CUSTODY_STATES = ("OPEN", "FROZEN", "AMENDED", "SUPERSEDED", "CORRUPTED")
FROZEN_STATES = {"FROZEN", "AMENDED", "SUPERSEDED", "CORRUPTED"}


def content_hash(content: str | bytes) -> str:
    """Return the sha256 hex digest for the given content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ArtifactReference:
    """A single hashed artifact reference inside a custody record."""

    role: str
    path: str
    content_hash: str
    artifact_hash: str = ""  # hash of the reference envelope itself, unused for resolution


@dataclass
class EvidenceCustody:
    """Custody record for one evaluation evidence bundle."""

    custody_id: str
    state: str = "OPEN"
    created_at: str = field(default_factory=_now_iso)
    frozen_at: str | None = None
    amended_at: str | None = None
    superseded_at: str | None = None
    corrupted_at: str | None = None
    stored_literal_expires_at: str | None = None
    artifacts: dict[str, ArtifactReference] = field(default_factory=dict)
    literal_response_hash: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "custody_id": self.custody_id,
            "state": self.state,
            "created_at": self.created_at,
            "frozen_at": self.frozen_at,
            "amended_at": self.amended_at,
            "superseded_at": self.superseded_at,
            "corrupted_at": self.corrupted_at,
            "stored_literal_expires_at": self.stored_literal_expires_at,
            "artifacts": {
                role: {
                    "role": ref.role,
                    "path": ref.path,
                    "content_hash": ref.content_hash,
                }
                for role, ref in self.artifacts.items()
            },
            "literal_response_hash": self.literal_response_hash,
            "notes": self.notes,
        }

    def freeze(self) -> None:
        if self.state != "OPEN":
            raise ValueError(f"cannot freeze custody in state {self.state}")
        self.state = "FROZEN"
        self.frozen_at = _now_iso()

    def amend(self, note: str = "") -> "EvidenceCustody":
        if self.state != "FROZEN":
            raise ValueError(f"cannot amend custody in state {self.state}")
        self.state = "AMENDED"
        self.amended_at = _now_iso()
        if note:
            self.notes = f"{self.notes}; amended: {note}".strip("; ")
        return self

    def supersede(self, note: str = "") -> "EvidenceCustody":
        if self.state not in {"FROZEN", "AMENDED"}:
            raise ValueError(f"cannot supersede custody in state {self.state}")
        self.state = "SUPERSEDED"
        self.superseded_at = _now_iso()
        if note:
            self.notes = f"{self.notes}; superseded: {note}".strip("; ")
        return self

    def mark_corrupted(self, reason: str) -> None:
        if self.state == "CORRUPTED":
            return
        self.state = "CORRUPTED"
        self.corrupted_at = _now_iso()
        self.notes = f"{self.notes}; corrupted: {reason}".strip("; ")


class CustodyError(Exception):
    pass


def create_custody(
    custody_id: str,
    artifacts: dict[str, Path | str],
    *,
    literal_response: str | None = None,
    literal_expires_at: str | None = None,
) -> EvidenceCustody:
    """Create an OPEN custody record hashing every supplied artifact.

    ``artifacts`` maps a role name to either a filesystem path or raw content.
    Roles follow the provenance vocabulary: ``case``, ``prompt_template``,
    ``assembled_context``, ``criteria``, ``memory``, ``policy``,
    ``partition_manifest``, ``response_literal``.
    """
    refs: dict[str, ArtifactReference] = {}
    literal_hash: str | None = None

    for role, source in artifacts.items():
        if role == "response_literal":
            if not isinstance(source, str):
                raise CustodyError("response_literal must be supplied as string content")
            literal_hash = content_hash(source)
            refs[role] = ArtifactReference(role=role, path="<inline>", content_hash=literal_hash)
            continue
        path = Path(source) if not isinstance(source, Path) else source
        if not path.is_file():
            raise CustodyError(f"artifact for role '{role}' not found: {path}")
        refs[role] = ArtifactReference(role=role, path=str(path), content_hash=content_hash(path.read_bytes()))

    if literal_response is not None:
        literal_hash = content_hash(literal_response)
        refs["response_literal"] = ArtifactReference(role="response_literal", path="<inline>", content_hash=literal_hash)

    return EvidenceCustody(
        custody_id=custody_id,
        artifacts=refs,
        literal_response_hash=literal_hash,
        stored_literal_expires_at=literal_expires_at,
    )


def resolve_custody(
    custody: EvidenceCustody,
    *,
    base_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve a custody record against the filesystem and its expiry.

    Returns a resolution report. Read-only: it never mutates the record except
    to mark it CORRUPTED when stored content no longer matches its hash.
    """
    now = now or datetime.now(timezone.utc)
    issues: list[str] = []
    resolved: dict[str, str] = {}
    missing: list[str] = []
    modified: list[str] = []

    for role, ref in custody.artifacts.items():
        if role == "response_literal":
            continue
        path = Path(ref.path)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        if not path.is_file():
            missing.append(role)
            issues.append(f"missing artifact for role '{role}': {path}")
            continue
        actual = content_hash(path.read_bytes())
        if actual != ref.content_hash:
            modified.append(role)
            issues.append(f"hash mismatch for role '{role}'")
            continue
        resolved[role] = actual

    if custody.literal_response_hash is not None and "response_literal" in custody.artifacts:
        resolved["response_literal"] = custody.literal_response_hash

    if missing or modified:
        custody.mark_corrupted("; ".join(issues))

    literal_expired = False
    if custody.stored_literal_expires_at:
        try:
            expires = datetime.fromisoformat(custody.stored_literal_expires_at)
        except ValueError:
            issues.append("unparseable stored_literal_expires_at")
            literal_expired = True
        else:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if now >= expires:
                literal_expired = True
                issues.append("stored literal expired; downgrade to hash-only")

    return {
        "custody_id": custody.custody_id,
        "state": custody.state,
        "resolved": resolved,
        "missing": missing,
        "modified": modified,
        "literal_expired": literal_expired,
        "evidence_mode": "none" if custody.state == "CORRUPTED" else ("hash_only" if literal_expired else "literal"),
        "provenance_status": "unverified" if custody.state == "CORRUPTED" else ("limited" if literal_expired else "verified"),
        "issues": issues,
    }


def enforce_frozen_immutability(custody: EvidenceCustody, new_artifacts: dict[str, Path | str]) -> None:
    """Raise if a caller attempts to mutate a frozen custody record."""
    if custody.state in FROZEN_STATES:
        raise CustodyError(f"custody {custody.custody_id} is {custody.state}; content is immutable")
    # OPEN records accept additive artifact registration.
    for role, source in new_artifacts.items():
        if role in custody.artifacts:
            raise CustodyError(f"role '{role}' already registered in OPEN custody {custody.custody_id}")
        if role == "response_literal":
            if not isinstance(source, str):
                raise CustodyError("response_literal must be string content")
            custody.artifacts[role] = ArtifactReference(role=role, path="<inline>", content_hash=content_hash(source))
            custody.literal_response_hash = content_hash(source)
            continue
        path = Path(source)
        if not path.is_file():
            raise CustodyError(f"artifact for role '{role}' not found: {path}")
        custody.artifacts[role] = ArtifactReference(role=role, path=str(path), content_hash=content_hash(path.read_bytes()))
