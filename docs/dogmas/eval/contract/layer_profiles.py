"""Serialized Layer A control and Layer B criteria profiles.

Implements task 2.1 (serialized profile definitions consumed by an evaluation
record) and the guard that enforces task 2.3 (Layer C recommendations cannot
override Layer A/B controls or authorize irreversible operations).

The profiles are standalone, schema-validated artifacts. Evaluation and
trajectory records reference them by ``profile_id`` (their ``layer_a_profile``
and ``layer_b_criteria_version`` fields). The guard evaluates Layer C
recommendations against the active Layer A and Layer B profiles; it never
relies on the model's safety justification, only on the machine-side profile
declarations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from .canonical import digest

LAYER_A_CONTROL_NAMES = frozenset({
    "tool_permissions",
    "secret_redaction",
    "audit_logging",
    "scope_checks",
    "phase_gates",
    "irreversible_confirmation",
})

LAYER_B_CRITERION_CLASSES = frozenset({"rule", "incident", "hypothesis", "example"})

PROFILE_SCHEMA_VERSION = "v1"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> Any:
    """Strip integrity fields and return a JSON-safe canonical structure."""
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value) if key != "profile_hash"}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _hash_record(record: dict[str, Any]) -> str:
    return digest(_canonical(record))


@dataclass(frozen=True)
class LayerAControl:
    control_name: str
    enabled: bool
    mechanism: str
    version: str

    def __post_init__(self) -> None:
        if self.control_name not in LAYER_A_CONTROL_NAMES:
            raise ValueError(f"unknown Layer A control: {self.control_name}")
        if not self.mechanism:
            raise ValueError("control mechanism must be a non-empty string")
        if not self.version:
            raise ValueError("control version must be a non-empty string")

    def to_record(self) -> dict[str, Any]:
        return {
            "control_name": self.control_name,
            "enabled": self.enabled,
            "mechanism": self.mechanism,
            "version": self.version,
        }


@dataclass(frozen=True)
class LayerBCriterion:
    rule_id: str
    version: str
    normative: bool
    klass: str = "rule"

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("rule_id must be a non-empty string")
        if not self.version:
            raise ValueError("criterion version must be a non-empty string")
        if self.klass not in LAYER_B_CRITERION_CLASSES:
            raise ValueError(f"unknown criterion class: {self.klass}")

    def to_record(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "normative": self.normative,
            "class": self.klass,
        }


@dataclass(frozen=True)
class LayerAProfile:
    profile_id: str
    controls: tuple[LayerAControl, ...]
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id must be a non-empty string")
        names = [c.control_name for c in self.controls]
        if len(set(names)) != len(names):
            raise ValueError("Layer A profile must not declare the same control twice")
        if not self.controls:
            raise ValueError("Layer A profile must declare at least one control")

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "controls": [c.to_record() for c in sorted(self.controls, key=lambda c: c.control_name)],
            "created_at": self.created_at,
        }
        record["profile_hash"] = _hash_record(record)
        return record

    def enabled_controls(self) -> frozenset[str]:
        return frozenset(c.control_name for c in self.controls if c.enabled)

    def is_enabled(self, control_name: str) -> bool:
        for control in self.controls:
            if control.control_name == control_name:
                return control.enabled
        return False


@dataclass(frozen=True)
class LayerBProfile:
    profile_id: str
    criteria_version: str
    core_dogmas_version: str
    security_policy_version: str
    criteria: tuple[LayerBCriterion, ...]
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id must be a non-empty string")
        if not self.criteria_version:
            raise ValueError("criteria_version must be a non-empty string")
        if not self.core_dogmas_version:
            raise ValueError("core_dogmas_version must be a non-empty string")
        if not self.security_policy_version:
            raise ValueError("security_policy_version must be a non-empty string")
        if not self.criteria:
            raise ValueError("Layer B profile must declare at least one criterion")

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "criteria_version": self.criteria_version,
            "core_dogmas_version": self.core_dogmas_version,
            "security_policy_version": self.security_policy_version,
            "criteria": [c.to_record() for c in sorted(self.criteria, key=lambda c: c.rule_id)],
            "created_at": self.created_at,
        }
        record["profile_hash"] = _hash_record(record)
        return record

    def normative_rule_ids(self) -> frozenset[str]:
        return frozenset(c.rule_id for c in self.criteria if c.normative)

    def has_normative(self, rule_id: str) -> bool:
        for criterion in self.criteria:
            if criterion.rule_id == rule_id and criterion.normative:
                return True
        return False


DEFAULT_LAYER_A_CONTROLS: tuple[LayerAControl, ...] = (
    LayerAControl("tool_permissions", True, "claude_code.permission_policy", "v1"),
    LayerAControl("secret_redaction", True, "redact-output.py", "v1"),
    LayerAControl("audit_logging", True, "audit-log.sh", "v1"),
    LayerAControl("scope_checks", True, "scope-validator.sh", "v1"),
    LayerAControl("phase_gates", True, "phase-gate.sh", "v1"),
    LayerAControl("irreversible_confirmation", True, "dogmas/invariant_2", "v4.1"),
)


DEFAULT_LAYER_B_CRITERIA: tuple[LayerBCriterion, ...] = (
    LayerBCriterion("DOGMAS-CORE/INV-1", "v4.1", True, "rule"),
    LayerBCriterion("DOGMAS-CORE/INV-2", "v4.1", True, "rule"),
    LayerBCriterion("DOGMAS-CORE/INV-3", "v4.1", True, "rule"),
    LayerBCriterion("DOGMAS-CORE/INV-4", "v4.1", True, "rule"),
    LayerBCriterion("DOGMAS-CORE/INV-5", "v4.1", True, "rule"),
    LayerBCriterion("DOGMAS-CORE/INV-7", "v4.1", True, "rule"),
    LayerBCriterion("security-policy/I-01", "v1", True, "rule"),
    LayerBCriterion("security-policy/I-04", "v1", True, "rule"),
    LayerBCriterion("incident/2026-09-bootstrap-stale", "v1", False, "incident"),
)


def default_layer_a_profile() -> LayerAProfile:
    return LayerAProfile(
        profile_id="layer-a/default@v4.1",
        controls=DEFAULT_LAYER_A_CONTROLS,
    )


def default_layer_b_profile() -> LayerBProfile:
    return LayerBProfile(
        profile_id="layer-b/dogmas-core@v4.1+security@v1",
        criteria_version="v4.1",
        core_dogmas_version="v4.1",
        security_policy_version="v1",
        criteria=DEFAULT_LAYER_B_CRITERIA,
    )


# ---------------------------------------------------------------------------
# Layer C recommendation + authority guard (task 2.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LayerCRecommendation:
    """A Layer C proposal. The guard evaluates this against active A/B profiles."""

    recommendation_id: str
    action: str  # e.g. "disable_control", "weaken_redaction", "authorize_irreversible", "modify_layer_b"
    target: str = ""
    justification: str = ""
    requires_human_approval: bool = False


@dataclass(frozen=True)
class GuardDecision:
    accepted: bool
    reason: str
    rejected_field: str = ""


def evaluate_recommendation(
    layer_a: LayerAProfile,
    layer_b: LayerBProfile,
    recommendation: LayerCRecommendation,
) -> GuardDecision:
    """Decide whether ``recommendation`` may be applied.

    Implements the "Machine controls remain authoritative" and "Layer C may
    propose, never apply" requirements. A recommendation that disables an
    enabled Layer A control, weakens redaction, bypasses a scope or phase
    gate, authorizes an irreversible action, or attempts to modify a
    normative Layer B criterion without explicit human approval is rejected.
    """
    if recommendation.action == "disable_control":
        target = recommendation.target
        if layer_a.is_enabled(target):
            return GuardDecision(
                accepted=False,
                reason=f"Layer C cannot disable enabled Layer A control: {target}",
                rejected_field=f"layer_a.controls.{target}",
            )
        return GuardDecision(accepted=True, reason="control already disabled")

    if recommendation.action == "weaken_redaction":
        if layer_a.is_enabled("secret_redaction"):
            return GuardDecision(
                accepted=False,
                reason="Layer C cannot weaken enabled secret_redaction control",
                rejected_field="layer_a.controls.secret_redaction",
            )
        return GuardDecision(accepted=True, reason="redaction already weakened")

    if recommendation.action == "bypass_scope_gate":
        if layer_a.is_enabled("scope_checks") or layer_a.is_enabled("phase_gates"):
            return GuardDecision(
                accepted=False,
                reason="Layer C cannot bypass enabled scope_checks or phase_gates",
                rejected_field="layer_a.controls.scope_checks",
            )
        return GuardDecision(accepted=True, reason="scope gates already disabled")

    if recommendation.action == "authorize_irreversible":
        if layer_a.is_enabled("irreversible_confirmation"):
            return GuardDecision(
                accepted=False,
                reason="Layer C cannot authorize irreversible operations; separate confirmation required",
                rejected_field="layer_a.controls.irreversible_confirmation",
            )
        return GuardDecision(accepted=True, reason="irreversible_confirmation already disabled")

    if recommendation.action == "modify_layer_b":
        if not recommendation.requires_human_approval:
            return GuardDecision(
                accepted=False,
                reason="Layer C cannot modify Layer B without explicit human approval",
                rejected_field="layer_b.criteria",
            )
        return GuardDecision(
            accepted=True,
            reason="Layer B modification approved by human; pending regression re-run",
        )

    if recommendation.action == "propose_only":
        return GuardDecision(accepted=True, reason="proposal-only action; no override")

    return GuardDecision(accepted=False, reason=f"unknown action: {recommendation.action}")


def capture_for_record(
    layer_a: LayerAProfile,
    layer_b: LayerBProfile,
) -> dict[str, str]:
    """Return the values an evaluation/trajectory record should carry.

    These are identifier strings, not the full profiles, and they are
    descriptive metadata only. Enforcement never depends on the record
    declaring a particular profile.
    """
    return {
        "layer_a_profile": layer_a.profile_id,
        "layer_b_criteria_version": f"{layer_b.criteria_version}+{layer_b.profile_id}",
        "layer_c_memory_version": "n/a",
    }


def validate_profile_pair(
    layer_a: LayerAProfile,
    layer_b: LayerBProfile,
    *,
    required_controls: Iterable[str] = LAYER_A_CONTROL_NAMES,
) -> list[str]:
    """Static checks a deployment should run before activating a profile pair."""
    errors: list[str] = []
    enabled = layer_a.enabled_controls()
    for control_name in required_controls:
        if control_name not in {c.control_name for c in layer_a.controls}:
            errors.append(f"Layer A profile is missing required control: {control_name}")
            continue
        if control_name not in enabled:
            errors.append(f"Layer A control {control_name} must be enabled")
    if not layer_b.criteria:
        errors.append("Layer B profile has no criteria")
    if not any(c.normative for c in layer_b.criteria):
        errors.append("Layer B profile has no normative criteria")
    return errors