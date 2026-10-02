from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from p2_4 import (
    ArtifactFieldClass,
    ArtifactLanguagePolicy,
    AutomationThreshold,
    Comparability,
    ConfigurationSignature,
    FragilityProtocol,
    IntersectionStatus,
    ModelJudgment,
    configuration_hash,
    cross_model_intersection,
    evaluate_phase_transition,
    intersect_models,
    measure_format_fragility,
)


def make_signature(served: str = "model-a", sampling: str = "0.7") -> ConfigurationSignature:
    return ConfigurationSignature("requested", served, {"temperature": sampling}, "en")


def test_configuration_signature_comparable_when_equal() -> None:
    first = make_signature()
    second = make_signature()
    comparability, differences = first.compare(second)
    assert comparability == Comparability.COMPARABLE
    assert differences == []


def test_configuration_signature_non_comparable_on_unknown_served() -> None:
    first = make_signature(served="model-a")
    second = make_signature(served="unknown")
    comparability, differences = first.compare(second)
    assert comparability == Comparability.NON_COMPARABLE
    assert "served_model_unknown" in differences


def test_configuration_signature_non_comparable_on_different_served() -> None:
    first = make_signature(served="model-a")
    second = make_signature(served="model-b")
    comparability, differences = first.compare(second)
    assert comparability == Comparability.NON_COMPARABLE
    assert "served_model_different" in differences


def test_configuration_signature_non_comparable_on_different_sampling() -> None:
    first = make_signature(sampling="0.7")
    second = make_signature(sampling="0.9")
    comparability, differences = first.compare(second)
    assert comparability == Comparability.NON_COMPARABLE
    assert "sampling_different" in differences


def test_configuration_signature_non_comparable_on_different_language() -> None:
    first = ConfigurationSignature("requested", "model-a", {"temperature": "0.7"}, "en")
    second = ConfigurationSignature("requested", "model-a", {"temperature": "0.7"}, "es")
    comparability, differences = first.compare(second)
    assert comparability == Comparability.NON_COMPARABLE
    assert "case_language_different" in differences


def test_configuration_hash_is_deterministic() -> None:
    signature = make_signature()
    assert configuration_hash(signature) == configuration_hash(signature)


def test_intersect_models_agrees_when_outcomes_match() -> None:
    signature = make_signature()
    judgments = [
        ModelJudgment("model-a", True, signature),
        ModelJudgment("model-b", True, signature),
    ]
    result = intersect_models(judgments, case_id="case-1")
    assert result.status == IntersectionStatus.AGREEMENT
    assert result.dissenting_models == ()


def test_intersect_models_flags_frontier_dissent() -> None:
    signature = make_signature()
    judgments = [
        ModelJudgment("model-a", True, signature),
        ModelJudgment("model-b", False, signature),
    ]
    result = intersect_models(judgments, case_id="case-2")
    assert result.status == IntersectionStatus.FRONTIER
    assert "model-b" in result.dissenting_models
    assert "human review" in result.reason


def test_intersect_models_unresolved_on_missing_outcome() -> None:
    signature = make_signature()
    judgments = [
        ModelJudgment("model-a", None, signature),
        ModelJudgment("model-b", True, signature),
    ]
    result = intersect_models(judgments, case_id="case-3")
    assert result.status == IntersectionStatus.UNRESOLVED


def test_intersect_models_non_comparable_on_configuration_mismatch() -> None:
    first = make_signature(served="model-a")
    second = make_signature(served="model-b")
    judgments = [
        ModelJudgment("model-a", True, first),
        ModelJudgment("model-b", False, second),
    ]
    result = intersect_models(judgments, case_id="case-4")
    assert result.status == IntersectionStatus.NON_COMPARABLE
    assert "configuration mismatch" in result.reason


def test_cross_model_intersection_report() -> None:
    signature = make_signature()
    cases = {
        "case-1": [
            ModelJudgment("model-a", True, signature),
            ModelJudgment("model-b", True, signature),
        ],
        "case-2": [
            ModelJudgment("model-a", True, signature),
            ModelJudgment("model-b", False, signature),
        ],
    }
    report = cross_model_intersection(cases)
    assert report["counts"]["agreement"] == 1
    assert report["counts"]["frontier"] == 1
    assert "case-2" in report["frontier_cases"]
    assert "case-2" in report["human_review_required"]


def test_fragility_protocol_requires_positive_rewording_count() -> None:
    with pytest.raises(ValueError, match="positive"):
        FragilityProtocol(rewording_count=0, sensitivity_threshold=0.5, semantic_equivalence_review="human")


def test_fragility_protocol_requires_valid_threshold() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        FragilityProtocol(rewording_count=3, sensitivity_threshold=1.5, semantic_equivalence_review="human")


def test_fragility_protocol_requires_review() -> None:
    with pytest.raises(ValueError, match="required"):
        FragilityProtocol(rewording_count=3, sensitivity_threshold=0.5, semantic_equivalence_review="")


def test_measure_format_fragility_low_sensitivity() -> None:
    protocol = FragilityProtocol(rewording_count=3, sensitivity_threshold=0.5, semantic_equivalence_review="human")
    result = measure_format_fragility(True, [True, True, False], protocol)
    assert result.flip_count == 1
    assert result.sensitivity == pytest.approx(1 / 3)
    assert result.status == "low_fragility"


def test_measure_format_fragility_high_sensitivity() -> None:
    protocol = FragilityProtocol(rewording_count=4, sensitivity_threshold=0.5, semantic_equivalence_review="human")
    result = measure_format_fragility(True, [False, False, True, False], protocol)
    assert result.flip_count == 3
    assert result.sensitivity == pytest.approx(0.75)
    assert result.status == "high_fragility"


def test_measure_format_fragility_requires_matching_count() -> None:
    protocol = FragilityProtocol(rewording_count=3, sensitivity_threshold=0.5, semantic_equivalence_review="human")
    with pytest.raises(ValueError, match="does not match"):
        measure_format_fragility(True, [True, False], protocol)


def test_automation_threshold_requires_positive_samples() -> None:
    with pytest.raises(ValueError, match="positive"):
        AutomationThreshold(min_samples_per_category=0, max_confidence_interval_width=0.1, min_important_difference=0.05)


def test_automation_threshold_requires_valid_width() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        AutomationThreshold(min_samples_per_category=5, max_confidence_interval_width=0, min_important_difference=0.05)


def test_evaluate_phase_transition_eligible() -> None:
    threshold = AutomationThreshold(min_samples_per_category=5, max_confidence_interval_width=0.1, min_important_difference=0.05)
    result = evaluate_phase_transition({"comprehension": 10, "correction": 8}, 0.08, 0.06, threshold)
    assert result["status"] == "eligible"
    assert result["under_sampled_categories"] == []
    assert result["width_ok"] is True
    assert result["effect_ok"] is True


def test_evaluate_phase_transition_blocked_by_under_sampled() -> None:
    threshold = AutomationThreshold(min_samples_per_category=5, max_confidence_interval_width=0.1, min_important_difference=0.05)
    result = evaluate_phase_transition({"comprehension": 3, "correction": 8}, 0.08, 0.06, threshold)
    assert result["status"] == "blocked"
    assert "comprehension" in result["under_sampled_categories"]


def test_evaluate_phase_transition_blocked_by_wide_interval() -> None:
    threshold = AutomationThreshold(min_samples_per_category=5, max_confidence_interval_width=0.1, min_important_difference=0.05)
    result = evaluate_phase_transition({"comprehension": 10, "correction": 8}, 0.15, 0.06, threshold)
    assert result["status"] == "blocked"
    assert result["width_ok"] is False


def test_evaluate_phase_transition_blocked_by_small_effect() -> None:
    threshold = AutomationThreshold(min_samples_per_category=5, max_confidence_interval_width=0.1, min_important_difference=0.05)
    result = evaluate_phase_transition({"comprehension": 10, "correction": 8}, 0.08, 0.03, threshold)
    assert result["status"] == "blocked"
    assert result["effect_ok"] is False


def test_artifact_language_policy_classifies_fields() -> None:
    policy = ArtifactLanguagePolicy(machine_language="en")
    assert policy.classify("case_text") == ArtifactFieldClass.CASE_ORIGINAL
    assert policy.classify("human_guidance") == ArtifactFieldClass.OPERATOR_FACING
    assert policy.classify("case_hash") == ArtifactFieldClass.MACHINE


def test_artifact_language_policy_validates_machine_language() -> None:
    policy = ArtifactLanguagePolicy(machine_language="en")
    violations = policy.validate_machine_language("en", {"case_hash": "en", "case_text": "es"})
    assert violations == []
    violations = policy.validate_machine_language("en", {"case_hash": "es", "case_text": "es"})
    assert len(violations) == 1
    assert "case_hash" in violations[0]
