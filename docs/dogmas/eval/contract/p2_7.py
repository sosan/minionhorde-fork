"""P2.7 contracts for memory lifecycle and operational integrity."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"
    REDACTED = "redacted"
    CONFLICTED = "conflicted"


class ConflictStatus(StrEnum):
    NONE = "none"
    DETECTED = "detected"
    ESCALATED = "escalated"


class AuditSeverity(StrEnum):
    INFO = "info"
    SECURITY = "security"


def content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def token_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


@dataclass
class MemoryEntry:
    entry_id: str
    content: str
    decision_principle: str
    priority: int = 0
    status: MemoryStatus = MemoryStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str | None = None
    model_version: str = "unknown"
    criteria_version: str = "unknown"
    policy_version: str = "unknown"
    tooling_version: str = "unknown"
    source_hash: str = ""
    redaction_events: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.entry_id or not self.decision_principle:
            raise ValueError("entry_id and decision_principle are required")
        if not self.source_hash:
            self.source_hash = content_hash(self.content)
        if self.priority < 0:
            raise ValueError("priority must be non-negative")

    @property
    def tokens(self) -> int:
        return token_count(self.content)

    def is_stale(self, *, now: datetime | None = None, context: Mapping[str, str] | None = None) -> bool:
        if self.status in {MemoryStatus.STALE, MemoryStatus.ARCHIVED, MemoryStatus.REDACTED}:
            return True
        now = now or datetime.now(timezone.utc)
        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if now >= expiry:
                return True
        if context:
            versions = {
                "model_version": self.model_version,
                "criteria_version": self.criteria_version,
                "policy_version": self.policy_version,
                "tooling_version": self.tooling_version,
            }
            if any(key in context and context[key] != value for key, value in versions.items()):
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "decision_principle": self.decision_principle,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "model_version": self.model_version,
            "criteria_version": self.criteria_version,
            "policy_version": self.policy_version,
            "tooling_version": self.tooling_version,
            "source_hash": self.source_hash,
            "redaction_events": list(self.redaction_events),
        }


@dataclass(frozen=True)
class ConflictReport:
    principle: str
    entry_ids: tuple[str, ...]
    status: ConflictStatus
    winner_id: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "principle": self.principle,
            "entry_ids": list(self.entry_ids),
            "status": self.status.value,
            "winner_id": self.winner_id,
            "reason": self.reason,
        }


def detect_conflicts(entries: Sequence[MemoryEntry], *, escalate: bool = True) -> list[ConflictReport]:
    """Detect competing active entries and apply configured priority precedence."""
    grouped: dict[str, list[MemoryEntry]] = {}
    for entry in entries:
        if entry.status == MemoryStatus.ACTIVE:
            grouped.setdefault(entry.decision_principle, []).append(entry)
    reports: list[ConflictReport] = []
    for principle, candidates in grouped.items():
        if len(candidates) < 2:
            continue
        ordered = sorted(candidates, key=lambda item: (-item.priority, item.entry_id))
        winner = ordered[0]
        status = ConflictStatus.ESCALATED if escalate else ConflictStatus.DETECTED
        reports.append(ConflictReport(principle, tuple(item.entry_id for item in ordered), status, winner.entry_id, "multiple active entries; priority precedence applied and human review required" if escalate else "multiple active entries"))
    return reports


@dataclass(frozen=True)
class InjectionBudget:
    max_entries: int
    max_tokens: int

    def __post_init__(self) -> None:
        if self.max_entries < 1 or self.max_tokens < 1:
            raise ValueError("memory injection budget must be positive")


@dataclass(frozen=True)
class InjectionResult:
    selected_ids: tuple[str, ...]
    pruned_ids: tuple[str, ...]
    total_tokens: int
    manifest_hash: str
    human_confirmation_required: bool


def apply_injection_budget(entries: Sequence[MemoryEntry], budget: InjectionBudget) -> InjectionResult:
    """Select by priority without exceeding entry/token limits."""
    selected: list[MemoryEntry] = []
    pruned: list[MemoryEntry] = []
    total = 0
    for entry in sorted(entries, key=lambda item: (-item.priority, item.entry_id)):
        if entry.status != MemoryStatus.ACTIVE:
            pruned.append(entry)
        elif len(selected) >= budget.max_entries or total + entry.tokens > budget.max_tokens:
            pruned.append(entry)
        else:
            selected.append(entry)
            total += entry.tokens
    selected_ids = tuple(item.entry_id for item in selected)
    pruned_ids = tuple(item.entry_id for item in pruned)
    manifest_hash = content_hash("|".join(selected_ids))
    return InjectionResult(selected_ids, pruned_ids, total, manifest_hash, bool(pruned_ids))


_SECRET_PATTERNS = (
    ("api_key", re.compile(r"(?i)\b(?:api[_ -]?key|token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{12,})")),
    ("password", re.compile(r"(?i)\bpassword\s*[:=]\s*['\"]?([^\s'\"]+)")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)),
)


def redact_secrets(entry: MemoryEntry) -> tuple[MemoryEntry, list[str]]:
    """Redact known secret patterns before an entry can be stored or injected."""
    redacted = entry.content
    events: list[str] = []
    for name, pattern in _SECRET_PATTERNS:
        replacement = "[REDACTED]"
        updated, count = pattern.subn(lambda match: replacement if name == "private_key" else match.group(0).replace(match.group(1), replacement), redacted)
        if count:
            events.extend([name] * count)
            redacted = updated
    if not events:
        return entry, []
    return replace(entry, content=redacted, status=MemoryStatus.REDACTED, source_hash=content_hash(redacted), redaction_events=entry.redaction_events + tuple(events)), events


@dataclass(frozen=True)
class AuditEvent:
    entry_id: str
    severity: AuditSeverity
    event: str
    details: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def audit_memory(entries: Sequence[MemoryEntry]) -> list[AuditEvent]:
    """Scan entries and report secret findings as security events."""
    events: list[AuditEvent] = []
    for entry in entries:
        _, findings = redact_secrets(entry)
        for finding in findings:
            events.append(AuditEvent(entry.entry_id, AuditSeverity.SECURITY, "secret_detected", finding))
    return events


def revalidate_memory_entry(entry: MemoryEntry, context: Mapping[str, str], *, now: datetime | None = None) -> MemoryEntry:
    """Mark an entry stale on TTL or model/criteria/policy/tooling change."""
    if entry.is_stale(now=now, context=context):
        entry.status = MemoryStatus.STALE
    return entry
