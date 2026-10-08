"""Append-only audit log for ``measure_judge_agreement`` calls.

Wraps ``contract.append_log.AppendLog`` so every agreement measurement
is recorded immutably with a chained hash. The protocol requires this
audit (see ``LABELED_SUBSET_PROTOCOL.md`` §"Failure modes / audit trail").

Storage layout (caller-provided):

    <journal_path>      — JSON-lines journal, one entry per measurement
    <journal_path>.manifest.json — sidecar with last_sequence + head_hash

The journal path is operator-supplied; tests pass ``tmp_path``. Production
runners are expected to point at a stable path under the eval working
directory, e.g. ``docs/dogmas/eval/audit/judge_agreement.jsonl``.

Example:
    audit = JudgeAgreementAudit(Path("audit/judge_agreement.jsonl"))
    audit.record_measurement(
        subset_id="review-opus-5-max-v1",
        detector_identity="claude-opus-5-max",
        detector_version="build-abc",
        kappa=0.85,
        n=48,
        threshold=0.8,
        min_subset_size=3,
        validated=True,
    )
    assert audit.verify_chain()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contract.append_log import AppendEntry, AppendLog

__all__ = ["JudgeAgreementAudit", "JudgeMeasurement"]

ENTRY_TYPE = "judge_agreement_measurement"


@dataclass(frozen=True)
class JudgeMeasurement:
    """Typed payload for a single agreement measurement."""

    subset_id: str
    detector_identity: str
    detector_version: str
    kappa: float
    n: int
    threshold: float
    min_subset_size: int
    validated: bool
    measured_at: str


class JudgeAgreementAudit:
    """Append-only audit for ``measure_judge_agreement`` calls."""

    def __init__(self, journal_path: Path) -> None:
        self.journal_path = Path(journal_path)
        self._log = AppendLog(self.journal_path)

    def record_measurement(
        self,
        *,
        subset_id: str,
        detector_identity: str,
        detector_version: str,
        kappa: float,
        n: int,
        threshold: float,
        min_subset_size: int,
        validated: bool,
        measured_at: str | None = None,
    ) -> AppendEntry:
        """Append a measurement entry to the journal."""
        measured_at = measured_at or datetime.now(timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "subset_id": subset_id,
            "detector_identity": detector_identity,
            "detector_version": detector_version,
            "kappa": kappa,
            "n": n,
            "threshold": threshold,
            "min_subset_size": min_subset_size,
            "validated": validated,
            "measured_at": measured_at,
        }
        return self._log.append(ENTRY_TYPE, payload)

    def verify_chain(self) -> bool:
        return self._log.verify_chain()

    def read_measurements(self) -> list[dict[str, Any]]:
        return [entry.payload for entry in self._log.entries]

    def recovered_count(self) -> int:
        return sum(
            1 for entry in self._log.entries if entry.entry_type == ENTRY_TYPE
        )