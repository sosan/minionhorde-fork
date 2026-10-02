from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_7 import (
    AuditSeverity,
    ConflictStatus,
    InjectionBudget,
    MemoryEntry,
    MemoryStatus,
    apply_injection_budget,
    audit_memory,
    detect_conflicts,
    redact_secrets,
    revalidate_memory_entry,
)


def entry(entry_id: str, principle: str = "principle", *, priority: int = 0, content: str = "keep evidence", **kwargs) -> MemoryEntry:
    return MemoryEntry(entry_id, content, principle, priority=priority, **kwargs)


def test_memory_entry_requires_identity_and_principle() -> None:
    with pytest.raises(ValueError, match="entry_id"):
        MemoryEntry("", "content", "principle")
    with pytest.raises(ValueError, match="decision_principle"):
        MemoryEntry("entry", "content", "")


def test_memory_entry_counts_tokens_and_hashes_content() -> None:
    current = entry("entry-1", content="one two three")
    assert current.tokens == 3
    assert len(current.source_hash) == 64


def test_conflict_detection_applies_priority_and_escalates() -> None:
    reports = detect_conflicts([entry("low", priority=1), entry("high", priority=3)])
    assert len(reports) == 1
    assert reports[0].status == ConflictStatus.ESCALATED
    assert reports[0].winner_id == "high"
    assert "human review" in reports[0].reason


def test_conflict_detection_can_record_without_escalation() -> None:
    reports = detect_conflicts([entry("a"), entry("b")], escalate=False)
    assert reports[0].status == ConflictStatus.DETECTED


def test_non_conflicting_principles_are_not_reported() -> None:
    reports = detect_conflicts([entry("a", "one"), entry("b", "two")])
    assert reports == []


def test_injection_budget_selects_priority_and_prunes() -> None:
    entries = [entry("low", priority=1, content="one two"), entry("high", priority=5, content="three"), entry("other", priority=2, content="four five")]
    result = apply_injection_budget(entries, InjectionBudget(max_entries=2, max_tokens=3))
    assert result.selected_ids == ("high", "other")
    assert result.pruned_ids == ("low",)
    assert result.total_tokens == 3
    assert result.human_confirmation_required is True
    assert len(result.manifest_hash) == 64


def test_injection_budget_rejects_nonpositive_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        InjectionBudget(0, 10)
    with pytest.raises(ValueError, match="positive"):
        InjectionBudget(1, 0)


def test_injection_budget_prunes_nonactive_entries() -> None:
    archived = entry("archived")
    archived.status = MemoryStatus.ARCHIVED
    result = apply_injection_budget([archived], InjectionBudget(2, 10))
    assert result.selected_ids == ()
    assert result.pruned_ids == ("archived",)


def test_redact_api_key_and_mark_entry_redacted() -> None:
    original = entry("secret", content="Use api_key=ABCDEF1234567890 for the service")
    redacted, events = redact_secrets(original)
    assert "ABCDEF1234567890" not in redacted.content
    assert "[REDACTED]" in redacted.content
    assert redacted.status == MemoryStatus.REDACTED
    assert "api_key" in events
    assert redacted.source_hash != original.source_hash


def test_redact_password_and_private_key() -> None:
    original = entry("secrets", content="password: hunter2\n-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----")
    redacted, events = redact_secrets(original)
    assert "hunter2" not in redacted.content
    assert "PRIVATE KEY" not in redacted.content
    assert set(events) == {"password", "private_key"}


def test_redact_without_secrets_preserves_entry() -> None:
    original = entry("safe", content="Keep the evidence scoped")
    redacted, events = redact_secrets(original)
    assert redacted is original
    assert events == []


def test_audit_reports_security_events() -> None:
    events = audit_memory([entry("secret", content="token=ABCDEF1234567890")])
    assert len(events) == 1
    assert events[0].severity == AuditSeverity.SECURITY
    assert events[0].event == "secret_detected"


def test_revalidate_expired_entry_marks_stale() -> None:
    expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    current = entry("expired", expires_at=expired)
    revalidate_memory_entry(current, {}, now=datetime.now(timezone.utc))
    assert current.status == MemoryStatus.STALE


def test_revalidate_context_change_marks_stale() -> None:
    current = entry("context", model_version="model-v1", criteria_version="criteria-v1", policy_version="policy-v1", tooling_version="tools-v1")
    revalidate_memory_entry(current, {"model_version": "model-v2"})
    assert current.status == MemoryStatus.STALE


def test_revalidate_unchanged_context_keeps_active() -> None:
    current = entry("active", model_version="model-v1")
    revalidate_memory_entry(current, {"model_version": "model-v1"})
    assert current.status == MemoryStatus.ACTIVE


def test_stale_status_is_excluded_from_injection() -> None:
    current = entry("stale")
    current.status = MemoryStatus.STALE
    result = apply_injection_budget([current], InjectionBudget(2, 10))
    assert result.selected_ids == ()
    assert result.pruned_ids == ("stale",)
