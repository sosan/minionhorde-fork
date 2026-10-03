"""Runtime contract for bounded Socratic trajectories and recovery evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import threading
from typing import Any

STATES = {
    "INIT",
    "INTERPRET",
    "REFORMULATE",
    "CHALLENGE",
    "EVIDENCE_CHECK",
    "CORRECT",
    "AUDIT",
    "HUMAN_INPUT",
    "COMPLETED",
    "INTERRUPTED",
    "ABORTED",
}
TERMINAL = {"COMPLETED", "INTERRUPTED", "ABORTED"}
TRANSITIONS = {
    "INIT": {"INTERPRET", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "INTERPRET": {"REFORMULATE", "CHALLENGE", "EVIDENCE_CHECK", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "REFORMULATE": {"CHALLENGE", "EVIDENCE_CHECK", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "CHALLENGE": {"EVIDENCE_CHECK", "CORRECT", "HUMAN_INPUT", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "EVIDENCE_CHECK": {"CORRECT", "AUDIT", "HUMAN_INPUT", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "CORRECT": {"AUDIT", "CHALLENGE", "EVIDENCE_CHECK", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "HUMAN_INPUT": {"INTERPRET", "EVIDENCE_CHECK", "AUDIT", "COMPLETED", "INTERRUPTED", "ABORTED"},
    "AUDIT": {"COMPLETED", "CHALLENGE", "HUMAN_INPUT", "INTERRUPTED", "ABORTED"},
}

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Turn:
    turn_id: str
    sequence: int
    state: str
    transition_cause: str
    claims: tuple[str, ...] = ()
    facts: tuple[str, ...] = ()
    inferences: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    challenges: tuple[str, ...] = ()
    changed_claims: tuple[str, ...] = ()
    preserved_claims: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    evidence_linked: bool = False
    created_at: str = field(default_factory=_now)

    @property
    def content_hash(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class AppendEntry:
    sequence: int
    entry_type: str
    payload: dict[str, Any]
    previous_hash: str
    entry_hash: str
    created_at: str = field(default_factory=_now)


class TrajectoryError(Exception):
    pass


class Trajectory:
    """Bounded, append-only trajectory with a verifiable hash chain."""

    def __init__(
        self,
        trajectory_id: str,
        *,
        max_turns: int = 32,
        no_progress_limit: int = 3,
        learning_loop: bool = False,
    ) -> None:
        self.trajectory_id = trajectory_id
        self.max_turns = max_turns
        self.no_progress_limit = no_progress_limit
        self.learning_loop = learning_loop
        self.state = "INIT"
        self._entries: list[AppendEntry] = []
        self._turns: list[Turn] = []
        self._seen_evidence: set[str] = set()
        self._seen_changed_claims: set[str] = set()
        self._no_progress_streak = 0
        self._lock = threading.Lock()

    @property
    def turns(self) -> tuple[Turn, ...]:
        return tuple(self._turns)

    @property
    def entries(self) -> tuple[AppendEntry, ...]:
        return tuple(self._entries)

    @property
    def head_hash(self) -> str:
        return self._entries[-1].entry_hash if self._entries else "0" * 64

    @property
    def no_progress_streak(self) -> int:
        return self._no_progress_streak

    def _append(self, entry_type: str, payload: dict[str, Any]) -> AppendEntry:
        sequence = len(self._entries)
        previous = self.head_hash
        envelope = {"sequence": sequence, "entry_type": entry_type, "payload": payload, "previous_hash": previous}
        entry = AppendEntry(sequence, entry_type, payload, previous, _hash(envelope))
        self._entries.append(entry)
        return entry

    def _evaluate_progress(self, turn: Turn) -> bool:
        """A turn makes progress when it adds new evidence refs or changes a claim.

        Repeated prompting that reuses the same evidence and does not change
        a claim is not progress; the trajectory is then aborted once the
        consecutive streak reaches ``no_progress_limit``.
        """
        new_evidence = set(turn.evidence_refs) - self._seen_evidence
        new_changes = set(turn.changed_claims) - self._seen_changed_claims
        self._seen_evidence.update(turn.evidence_refs)
        self._seen_changed_claims.update(turn.changed_claims)
        return bool(new_evidence or new_changes)

    def transition(self, target: str, cause: str) -> Turn:
        with self._lock:
            if target not in STATES:
                raise TrajectoryError(f"unknown state: {target}")
            if self.state in TERMINAL:
                raise TrajectoryError(f"trajectory is terminal: {self.state}")
            if target not in TRANSITIONS.get(self.state, set()):
                raise TrajectoryError(f"invalid transition {self.state} -> {target}")
            if self.learning_loop and self._turns:
                if not self._evaluate_progress(self._turns[-1]):
                    if self._no_progress_streak >= self.no_progress_limit:
                        self.state = "ABORTED"
                        self._append(
                            "state",
                            {
                                "state": "ABORTED",
                                "cause": "no_progress_exceeded",
                                "streak": self._no_progress_streak,
                            },
                        )
                        raise TrajectoryError(
                            f"no progress for {self._no_progress_streak} consecutive turns"
                        )
                    self._no_progress_streak += 1
                else:
                    self._no_progress_streak = 0
            if len(self._turns) >= self.max_turns:
                self.state = "ABORTED"
                self._append("state", {"state": "ABORTED", "cause": "max_turns_exceeded"})
                raise TrajectoryError("maximum turn budget exceeded")
            self.state = target
            turn = Turn(turn_id=f"{self.trajectory_id}:t{len(self._turns)+1}", sequence=len(self._turns), state=target, transition_cause=cause)
            self._turns.append(turn)
            self._append("turn", asdict(turn))
            return turn

    def amend_turn(self, turn_id: str, **changes: Any) -> Turn:
        with self._lock:
            if not self._turns or self._turns[-1].turn_id != turn_id:
                raise TrajectoryError("only the current turn may receive an append-only amendment")
            current = self._turns[-1]
            data = asdict(current)
            data.update(changes)
            updated = Turn(**data)
            self._turns[-1] = updated
            self._append("turn_amendment", asdict(updated))
            return updated

    def complete(self, cause: str = "audit_complete") -> None:
        self.transition("COMPLETED", cause)

    def interrupt(self, cause: str) -> None:
        if self.state in TERMINAL:
            raise TrajectoryError(f"trajectory is terminal: {self.state}")
        self.state = "INTERRUPTED"
        self._append("state", {"state": "INTERRUPTED", "cause": cause})

    def verify_chain(self) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        previous = "0" * 64
        for index, entry in enumerate(self._entries):
            if entry.sequence != index:
                reasons.append(f"sequence mismatch at {index}")
            if entry.previous_hash != previous:
                reasons.append(f"previous hash mismatch at {index}")
            envelope = {"sequence": entry.sequence, "entry_type": entry.entry_type, "payload": entry.payload, "previous_hash": entry.previous_hash}
            if entry.entry_hash != _hash(envelope):
                reasons.append(f"entry hash mismatch at {index}")
            previous = entry.entry_hash
        return not reasons, reasons

    def snapshot(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "state": self.state,
            "head_hash": self.head_hash,
            "entries": [asdict(entry) for entry in self._entries],
            "turns": [asdict(turn) for turn in self._turns],
        }


def detect_non_minimal_correction(before: dict[str, Any], after: dict[str, Any], allowed_fields: set[str]) -> dict[str, Any]:
    """Flag changed fields outside the classified recovery cause."""
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    extra = sorted(set(changed) - allowed_fields)
    return {"changed_fields": changed, "extra_fields": extra, "minimal": not extra}


def confirm_regression_failures(outcomes: list[bool], confirmations_required: int = 2) -> dict[str, Any]:
    """Require repeated failures before declaring a regression confirmed."""
    failures = sum(1 for outcome in outcomes if not outcome)
    confirmed = len(outcomes) >= confirmations_required and failures >= confirmations_required
    return {"confirmed": confirmed, "runs": len(outcomes), "failures": failures, "status": "confirmed" if confirmed else "unconfirmed"}
