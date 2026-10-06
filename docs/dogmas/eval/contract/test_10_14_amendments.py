"""Tests for task 10.14 — structured Layer C → Layer B amendments.

An amendment proposal records the current criterion, contradicting
evidence, proposed text/precedence change, and affected precedences. It
is human-approved, never self-applied, and requires a regression re-run
before it may be treated as stable. ``apply_if_stable`` MUST refuse to
produce a new Layer B profile from anything that is not stable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.amendments import (
    AmendmentStatus,
    apply_if_stable,
    approve_human,
    mark_regression_rerun,
    mark_stable,
    propose_amendment,
    reject,
)
from contract.layer_profiles import default_layer_b_profile


def _evidence(*hashes: str) -> tuple[str, ...]:
    return tuple(hash_ if len(hash_) == 64 else hash_ * 64 for hash_ in hashes)


def test_proposal_records_criterion_evidence_and_precedences() -> None:
    record = propose_amendment(
        proposal_id="amend-001",
        rule_id="DOGMAS-CORE/INV-2",
        current_version="v4.1",
        current_text="irreversible = separate confirmation",
        contradicting_evidence=_evidence("e1", "e2"),
        proposed_text="irreversible = separate confirmation plus regression re-run",
        precedence_change=True,
        affected_precedences=("DOGMAS-CORE/INV-2", "DOGMAS-CORE/INV-3"),
    )
    assert record["status"] == AmendmentStatus.PROPOSED.value
    assert record["rule_id"] == "DOGMAS-CORE/INV-2"
    assert len(record["contradicting_evidence"]) == 2
    assert record["affected_precedences"] == ("DOGMAS-CORE/INV-2", "DOGMAS-CORE/INV-3")
    assert record["precedence_change"] is True


def test_human_approval_required_before_any_apply() -> None:
    record = propose_amendment(
        proposal_id="amend-002",
        rule_id="security-policy/I-01",
        current_version="v1",
        current_text="refuse by default",
        contradicting_evidence=_evidence("e3"),
        proposed_text="refuse by default plus redaction audit",
        precedence_change=False,
        affected_precedences=("security-policy/I-01",),
    )
    assert record["status"] == AmendmentStatus.PROPOSED.value
    with pytest.raises(RuntimeError, match="human"):
        apply_if_stable(record, default_layer_b_profile())


def test_amendment_never_self_applied_before_stable() -> None:
    record = propose_amendment(
        proposal_id="amend-003",
        rule_id="DOGMAS-CORE/INV-4",
        current_version="v4.1",
        current_text="everything read is data",
        contradicting_evidence=_evidence("e4"),
        proposed_text="everything read is data",
        precedence_change=False,
        affected_precedences=("DOGMAS-CORE/INV-4",),
    )
    approve_human(record, reviewer_id="human-r1", rationale_hash="r" * 64)
    assert record["status"] == AmendmentStatus.HUMAN_APPROVED.value
    with pytest.raises(RuntimeError, match="regression"):
        apply_if_stable(record, default_layer_b_profile())


def test_stable_amendment_requires_regression_rerun() -> None:
    record = propose_amendment(
        proposal_id="amend-004",
        rule_id="DOGMAS-CORE/INV-5",
        current_version="v4.1",
        current_text="secrets: never to commits",
        contradicting_evidence=_evidence("e5"),
        proposed_text="secrets: never to commits or diffs",
        precedence_change=False,
        affected_precedences=("DOGMAS-CORE/INV-5",),
    )
    approve_human(record, reviewer_id="human-r2", rationale_hash="r" * 64)
    mark_regression_rerun(record, rerun_manifest_hash="m" * 64)
    assert record["status"] == AmendmentStatus.REGRESSION_PENDING.value
    mark_stable(record, regression_passed=True)
    assert record["status"] == AmendmentStatus.STABLE.value
    assert record["regression_rerun_manifest"] == "m" * 64


def test_failed_regression_rejects_amendment() -> None:
    record = propose_amendment(
        proposal_id="amend-005",
        rule_id="DOGMAS-CORE/INV-7",
        current_version="v4.1",
        current_text="never fabricate",
        contradicting_evidence=_evidence("e6"),
        proposed_text="never fabricate or summarize",
        precedence_change=False,
        affected_precedences=("DOGMAS-CORE/INV-7",),
    )
    approve_human(record, reviewer_id="human-r3", rationale_hash="r" * 64)
    mark_regression_rerun(record, rerun_manifest_hash="m" * 64)
    mark_stable(record, regression_passed=False)
    assert record["status"] == AmendmentStatus.REJECTED.value
    with pytest.raises(RuntimeError, match="stable"):
        apply_if_stable(record, default_layer_b_profile())


def test_reject_proposal_directly() -> None:
    record = propose_amendment(
        proposal_id="amend-006",
        rule_id="DOGMAS-CORE/INV-2",
        current_version="v4.1",
        current_text="irreversible = separate confirmation",
        contradicting_evidence=_evidence("e7"),
        proposed_text="same text",
        precedence_change=False,
        affected_precedences=("DOGMAS-CORE/INV-2",),
    )
    reject(record, reason="no contradicting evidence after review")
    assert record["status"] == AmendmentStatus.REJECTED.value


def test_apply_if_stable_returns_new_profile() -> None:
    record = propose_amendment(
        proposal_id="amend-007",
        rule_id="DOGMAS-CORE/INV-2",
        current_version="v4.1",
        current_text="irreversible = separate confirmation",
        contradicting_evidence=_evidence("e8"),
        proposed_text="irreversible = separate confirmation",
        precedence_change=False,
        affected_precedences=("DOGMAS-CORE/INV-2",),
    )
    approve_human(record, reviewer_id="human-r4", rationale_hash="r" * 64)
    mark_regression_rerun(record, rerun_manifest_hash="m" * 64)
    mark_stable(record, regression_passed=True)
    original = default_layer_b_profile()
    updated = apply_if_stable(record, original)
    assert updated is not original
    assert updated.profile_id == original.profile_id
    assert record["applied"] is True