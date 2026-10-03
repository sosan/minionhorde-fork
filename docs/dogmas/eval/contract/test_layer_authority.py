"""Layer C cannot override Layer A/B or authorize irreversible operations.

Implements task 2.3: the guard evaluates Layer C recommendations against the
active Layer A/B profiles and rejects any that would disable a control,
weaken redaction, bypass scope/phase gates, authorize irreversible actions,
or modify Layer B without human approval.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.layer_profiles import (
    LayerAControl,
    LayerAProfile,
    LayerBCriterion,
    LayerBProfile,
    LayerCRecommendation,
    default_layer_a_profile,
    default_layer_b_profile,
    evaluate_recommendation,
)


def _layer_a_with_disabled(*disabled: str) -> LayerAProfile:
    controls = tuple(
        LayerAControl(name, name not in disabled, "x", "v1")
        for name in (
            "tool_permissions",
            "secret_redaction",
            "audit_logging",
            "scope_checks",
            "phase_gates",
            "irreversible_confirmation",
        )
    )
    return LayerAProfile(profile_id="layer-a/disabled-test", controls=controls)


def _layer_b_with_no_normative() -> LayerBProfile:
    return LayerBProfile(
        profile_id="layer-b/incidents-only",
        criteria_version="v1",
        core_dogmas_version="v4.1",
        security_policy_version="v1",
        criteria=(LayerBCriterion("incident/only", "v1", False, "incident"),),
    )


def test_recommendation_to_disable_enabled_control_is_rejected() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(
            recommendation_id="r-1",
            action="disable_control",
            target="secret_redaction",
            justification="the hook slows me down",
        ),
    )
    assert not decision.accepted
    assert "secret_redaction" in decision.reason


def test_recommendation_to_disable_already_disabled_control_is_accepted() -> None:
    profile = _layer_a_with_disabled("secret_redaction")
    decision = evaluate_recommendation(
        profile,
        default_layer_b_profile(),
        LayerCRecommendation(recommendation_id="r-2", action="disable_control", target="secret_redaction"),
    )
    assert decision.accepted


def test_recommendation_to_weaken_enabled_redaction_is_rejected() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(
            recommendation_id="r-3",
            action="weaken_redaction",
            justification="model claims it can handle secrets safely",
        ),
    )
    assert not decision.accepted
    assert "secret_redaction" in decision.rejected_field


def test_guard_does_not_rely_on_model_justification() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(
            recommendation_id="r-4",
            action="disable_control",
            target="irreversible_confirmation",
            justification="trust me, the operation is reversible in practice",
        ),
    )
    assert not decision.accepted
    assert "irreversible_confirmation" in decision.reason


def test_recommendation_to_bypass_scope_gate_is_rejected() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(recommendation_id="r-5", action="bypass_scope_gate"),
    )
    assert not decision.accepted


def test_recommendation_to_authorize_irreversible_is_rejected() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(
            recommendation_id="r-6",
            action="authorize_irreversible",
            justification="I checked the file and it looks safe to force-push",
        ),
    )
    assert not decision.accepted
    assert "irreversible" in decision.reason.lower()


def test_recommendation_to_authorize_irreversible_when_control_disabled_is_accepted() -> None:
    profile = _layer_a_with_disabled("irreversible_confirmation")
    decision = evaluate_recommendation(
        profile,
        default_layer_b_profile(),
        LayerCRecommendation(recommendation_id="r-7", action="authorize_irreversible"),
    )
    assert decision.accepted


def test_recommendation_to_modify_layer_b_without_human_approval_is_rejected() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(
            recommendation_id="r-8",
            action="modify_layer_b",
            target="DOGMAS-CORE/INV-5",
            requires_human_approval=False,
        ),
    )
    assert not decision.accepted
    assert "human approval" in decision.reason


def test_recommendation_to_modify_layer_b_with_human_approval_is_accepted_but_pending_regression() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(
            recommendation_id="r-9",
            action="modify_layer_b",
            target="DOGMAS-CORE/INV-5",
            requires_human_approval=True,
        ),
    )
    assert decision.accepted
    assert "regression" in decision.reason


def test_unknown_action_is_rejected() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(recommendation_id="r-10", action="escalate_infinite"),
    )
    assert not decision.accepted


def test_propose_only_action_is_accepted() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        default_layer_b_profile(),
        LayerCRecommendation(recommendation_id="r-11", action="propose_only", target="INV-5"),
    )
    assert decision.accepted


def test_layer_b_without_normative_criteria_still_evaluated_but_never_authorizes_overrides() -> None:
    decision = evaluate_recommendation(
        default_layer_a_profile(),
        _layer_b_with_no_normative(),
        LayerCRecommendation(recommendation_id="r-12", action="disable_control", target="audit_logging"),
    )
    assert not decision.accepted
    assert "audit_logging" in decision.reason