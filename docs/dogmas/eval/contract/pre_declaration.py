"""Temporal pre-declaration registry (criterion 1 of the labeled-subset
protocol).

Requires that every case_id in the subset be fixed before any judge
output is observed. The registry records the subset's declaration
timestamp and compares it against ``judge_first_observed_at``; a judge
output that predates the declaration violates criterion 1.

Storage is an ``AppendLog`` journal so the declaration history is
append-only and tamper-evident.

Example:
    registry = PreDeclarationRegistry(Path("audit/pre_declaration.jsonl"))
    registry.declare("review-opus-5-max-v1", declared_at="2026-10-07T09:00:00+00:00")
    verdict = registry.validate_pre_declared(
        "review-opus-5-max-v1",
        judge_first_observed_at="2026-10-07T10:00:00+00:00",
    )
    assert verdict.valid
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from contract.append_log import AppendEntry, AppendLog

__all__ = ["PreDeclarationRegistry", "PreDeclarationRecord"]

ENTRY_TYPE = "subset_declared"


@dataclass(frozen=True)
class PreDeclarationRecord:
    subset_id: str
    declared_at: str


class PreDeclarationRegistry:
    """Append-only registry of subset pre-declaration timestamps."""

    def __init__(self, journal_path: Path) -> None:
        self.journal_path = Path(journal_path)
        self._log = AppendLog(self.journal_path)

    def declare(self, subset_id: str, declared_at: str) -> AppendEntry:
        """Record that ``subset_id`` was declared at ``declared_at``."""
        return self._log.append(
            ENTRY_TYPE,
            {"subset_id": subset_id, "declared_at": declared_at},
        )

    def _declared_at_for(self, subset_id: str) -> str | None:
        for entry in self._log.entries:
            if entry.entry_type == ENTRY_TYPE and entry.payload.get("subset_id") == subset_id:
                return str(entry.payload["declared_at"])
        return None

    def validate_pre_declared(
        self,
        subset_id: str,
        judge_first_observed_at: str,
    ) -> "PreDeclarationVerdict":
        """Return a verdict for criterion 1 (temporal pre-declaration)."""
        declared_at = self._declared_at_for(subset_id)
        if declared_at is None:
            return PreDeclarationVerdict(
                valid=False,
                issues=[
                    PreDeclarationIssue(
                        code="pre_declared_unknown",
                        severity="error",
                        message=f"subset {subset_id!r} has no declaration record",
                    )
                ],
            )
        if declared_at > judge_first_observed_at:
            return PreDeclarationVerdict(
                valid=False,
                issues=[
                    PreDeclarationIssue(
                        code="pre_declared_violation",
                        severity="error",
                        message=(
                            f"judge output observed at {judge_first_observed_at!r} "
                            f"predates declaration {declared_at!r} for {subset_id!r}"
                        ),
                    )
                ],
            )
        return PreDeclarationVerdict(valid=True, issues=[])


@dataclass(frozen=True)
class PreDeclarationIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class PreDeclarationVerdict:
    valid: bool
    issues: list[PreDeclarationIssue]